#!/usr/bin/env python3
"""Valida arquivos de Album Motion contra as regras da Apple Music (e as que a validação real já reprovou).

Uso:
  validate_motion.py 7891234567890_3x4.mov 7891234567890_1x1.mov [--cover capa.png] [--json]

Saída: PASS / WARN / FAIL por regra. Código de saída 1 se houver FAIL.
"""
import argparse, json, subprocess, sys
import numpy as np, cv2
for _s in (sys.stdout, sys.stderr):   # console legado do Windows (cp1252) quebra com emojis
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

SPEC = {
    '1x1': (3840, 3840),
    '3x4': (2048, 2732),
}
H264_MIN, H264_MAX = 45e6, 100e6


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path],
                         capture_output=True, text=True)
    return json.loads(out.stdout)


def decode_gray_small(path, size=64):
    """Luminância média por frame + frames reduzidos (para loop/flash)."""
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'scale={size}:{size},format=gray', '-f', 'rawvideo', '-'],
                       capture_output=True)
    a = np.frombuffer(p.stdout, np.uint8)
    n = len(a) // (size * size)
    return a[:n * size * size].reshape(n, size, size).astype(np.float32) / 255


def first_frame(path):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
    return cv2.imdecode(np.frombuffer(p.stdout, np.uint8), cv2.IMREAD_COLOR)


def flash_check(mean_luma, fps):
    """Aproximação da regra WCAG 2.3.1: >3 transições de luminância >10% em qualquer janela de 1 s."""
    d = np.diff(mean_luma)
    big = np.where(np.abs(d) > 0.10)[0]
    worst = 0
    for i in big:
        worst = max(worst, int(((big >= i) & (big < i + fps)).sum()))
    return float(np.abs(d).max()) if len(d) else 0.0, worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--cover')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    report, failed = [], False
    for path in a.files:
        res = []
        add = lambda status, rule, detail='': res.append({'status': status, 'rule': rule, 'detail': detail})
        info = probe(path)
        v = next((s for s in info.get('streams', []) if s['codec_type'] == 'video'), None)
        if not v:
            add('FAIL', 'stream de vídeo', 'não encontrado'); report.append({'file': path, 'results': res}); failed = True; continue
        fmt = '1x1' if '1x1' in path.lower() else '3x4' if '3x4' in path.lower() else None
        w, h = int(v['width']), int(v['height'])
        if fmt:
            add('PASS' if (w, h) == SPEC[fmt] else 'FAIL', f'resolução {fmt}', f'{w}x{h} (esperado {SPEC[fmt][0]}x{SPEC[fmt][1]})')
        else:
            add('WARN', 'formato', 'nome sem "1x1"/"3x4": não deu para conferir a resolução esperada')

        fnames = info['format']['format_name']
        add('PASS' if 'mov' in fnames else 'FAIL', 'container MOV/MP4 (QuickTime)', fnames.split(',')[0])
        sar = v.get('sample_aspect_ratio', '1:1')
        add('PASS' if sar in ('1:1', 'N/A', '0:1') and sar != '0:1' else 'FAIL', 'pixel quadrado (SAR 1:1)', f'SAR {sar}')

        codec = v['codec_name']
        prof = v.get('profile', '')
        dur = float(v.get('duration') or info['format']['duration'])
        add('PASS' if 8 <= dur <= 35 else 'FAIL', 'duração 8–35 s', f'{dur:.2f}s')
        if 8 <= dur < 15:
            add('WARN', 'duração < 15 s', 'o toolkit oficial aceita 8–35 s, mas algumas distribuidoras exigem 15–35 s: confirme com a sua')
        br = float(v.get('bit_rate') or info['format'].get('bit_rate') or 0)
        if codec == 'h264':
            add('PASS' if H264_MIN < br < H264_MAX else 'FAIL', 'bitrate H.264 entre 45 e 100 Mbps', f'{br / 1e6:.1f} Mbps')
            if path.lower().endswith('.mov'):
                add('WARN', 'H.264 em .mov', 'algumas distribuidoras esperam .mp4 para H.264 (ProRes em .mov é aceito em todas). Use --container mp4 ou --codec prores se a sua exigir')
        elif codec == 'prores':
            add('PASS' if any(k in prof for k in ('422', '4444', 'Proxy', 'LT', 'Standard', 'HQ')) else 'FAIL', 'ProRes 422 / 4444', prof)   # ffprobe chama o 422 de Proxy/LT/Standard/HQ
        else:
            add('FAIL', 'codec H.264 ou ProRes 422/4444', codec)
        add('PASS' if v.get('pix_fmt', '').startswith(('yuv420', 'yuv422', 'yuv444')) and 'a' not in v.get('pix_fmt', '')[-2:] else 'WARN',
            'sem canal alfa', v.get('pix_fmt', '?'))
        add('PASS' if v.get('color_space') in ('bt709', None) else 'WARN', 'Rec. 709', f"space={v.get('color_space')} trc={v.get('color_transfer')} prim={v.get('color_primaries')}")
        add('PASS' if not any(s['codec_type'] == 'audio' for s in info['streams']) else 'FAIL', 'sem áudio (mudo)')

        num, den = map(int, v['r_frame_rate'].split('/'))
        fps = num / den
        ok_fps = any(abs(fps - a_) < 0.02 for a_ in (23.976, 24, 25, 29.97, 30))
        add('PASS' if ok_fps else 'FAIL', 'frame rate permitido (23.976 / 24 / 25 / 29.97 / 30)', f'{fps:g} fps')

        frames = decode_gray_small(path)
        mean = frames.mean(axis=(1, 2))
        mx, burst = flash_check(mean, int(round(fps)))
        add('PASS' if burst <= 3 else 'FAIL', 'sem flashes/strobe (WCAG: ≤3 transições >10% por s)', f'maior salto de luminância {mx * 100:.1f}%, rajada máx {burst}')
        add('PASS' if mx < 0.08 else 'WARN', 'variação suave de luminância', f'{mx * 100:.1f}% entre frames consecutivos')

        # loop contínuo: diferença último->primeiro comparável às diferenças normais entre frames
        cons = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
        wrap = float(np.abs(frames[0] - frames[-1]).mean())
        typical = float(np.median(cons)) or 1e-6
        add('PASS' if wrap <= max(3 * typical, 0.01) else 'WARN', 'loop contínuo (último frame ≈ primeiro)', f'salto de fechamento {wrap:.4f} vs típico {typical:.4f}')
        solid = [i for i, fr in enumerate(frames) if fr.std() < 0.02]
        add('PASS' if not solid else 'FAIL', 'sem frames de cor sólida', f'{len(solid)} frames' if solid else '')

        if a.cover:
            _d = np.fromfile(a.cover, dtype=np.uint8)           # np.fromfile: caminhos Unicode no Windows
            cov = cv2.imdecode(_d, cv2.IMREAD_COLOR) if _d.size else None
            ff = first_frame(path)
            if cov is not None and ff is not None:
                if fmt == '3x4':   # a capa fica no miolo do canvas; busca fina do alinhamento vertical (1/4 de resolução)
                    q = 4
                    fs = cv2.resize(ff, (ff.shape[1] // q, ff.shape[0] // q), interpolation=cv2.INTER_AREA).astype(np.float32)
                    cs = cv2.resize(cov, (fs.shape[1], fs.shape[1]), interpolation=cv2.INTER_AREA).astype(np.float32)
                    best = min(np.abs(fs[y:y + cs.shape[0]] - cs).mean() for y in range(0, fs.shape[0] - cs.shape[0] + 1))
                else:
                    best = np.abs(ff.astype(np.float32) - cv2.resize(cov, (ff.shape[1], ff.shape[0])).astype(np.float32)).mean()
                add('PASS' if best < 6 else 'FAIL', 'primeiro frame == capa estática', f'diferença média {best:.2f}/255')

        failed |= any(r['status'] == 'FAIL' for r in res)
        report.append({'file': path, 'results': res})

    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        icon = {'PASS': '✅', 'WARN': '⚠️ ', 'FAIL': '❌'}
        for r in report:
            print(f"\n== {r['file']}")
            for x in r['results']:
                print(f"  {icon[x['status']]} {x['rule']}" + (f"  —  {x['detail']}" if x['detail'] else ''))
        print('\nRESULTADO:', 'REPROVADO' if failed else 'APROVADO (checagens locais; a validação oficial vem da distribuidora/Apple)')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
