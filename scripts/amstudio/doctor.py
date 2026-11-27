"""`studio.py doctor`: autodiagnóstico do ambiente + benchmark + autoteste ponta a ponta.

  studio.py doctor              verifica Python, FFmpeg (libx264/prores), bibliotecas, RAM, Unicode
  studio.py doctor --bench      + mede a velocidade desta máquina e ESTIMA o tempo de render
  studio.py doctor --selftest   + roda um mini fluxo completo (init → check → render curto) e confere o .mov
Cole a saída numa issue se algo falhar (ela não contém conteúdo das suas capas).
"""
import importlib, json, math, os, platform, shutil, subprocess, sys, tempfile, time
import numpy as np
from . import REF
from .compat import imwrite


def ram_gb():
    try:
        if sys.platform.startswith('win'):
            import ctypes
            class MS(ctypes.Structure):
                _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong), ('ullTotalPhys', ctypes.c_ulonglong),
                            ('ullAvailPhys', ctypes.c_ulonglong), ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                            ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong), ('sullAvailExtendedVirtual', ctypes.c_ulonglong)]
            m = MS(); m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullTotalPhys / 1e9, m.ullAvailPhys / 1e9
        total = os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE') / 1e9
        try:
            avail = os.sysconf('SC_AVPHYS_PAGES') * os.sysconf('SC_PAGE_SIZE') / 1e9
        except (ValueError, OSError):
            avail = None
        return total, avail
    except Exception:
        return None, None


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    except Exception:
        return None


class Report:
    def __init__(self): self.rows, self.failed = [], False
    def add(self, ok, name, detail='', hint=''):
        self.rows.append((ok, name, detail, hint))
        if ok is False: self.failed = True
    def print(self):
        icon = {True: '✅', False: '❌', None: '⚠️ '}
        for ok, name, detail, hint in self.rows:
            print(f'  {icon[ok]} {name}' + (f'  —  {detail}' if detail else ''))
            if hint and ok is not True: print(f'       ↳ {hint}')


def check_env(rep):
    rep.add(sys.version_info >= (3, 9), 'Python ≥ 3.9', platform.python_version(), 'Instale Python 3.9+ (3.11 recomendado)')
    rep.add(True, 'Sistema', f'{platform.system()} {platform.release()} · {platform.machine()} · {os.cpu_count()} CPUs')
    tot, av = ram_gb()
    if tot:
        rep.add(tot >= 3.5 or None, 'Memória RAM', f'{tot:.1f} GB total' + (f', {av:.1f} GB livres' if av else ''),
                'O 1:1 nativo usa ~1,3 GB (capa 3000) a ~2,8 GB (PSD 4000 px). Com pouca RAM use `--work-size 2048` e feche outros programas')
    for mod, pipname, req in (('cv2', 'opencv-python-headless', True), ('numpy', 'numpy', True), ('PIL', 'Pillow', True), ('psd_tools', 'psd-tools', True),
                              ('rembg', 'rembg', False), ('onnxruntime', 'onnxruntime', False)):
        try:
            m = importlib.import_module(mod)
            rep.add(True, f'biblioteca {mod}', getattr(m, '__version__', ''))
        except Exception as e:
            rep.add(False if req else None, f'biblioteca {mod}', 'ausente' if isinstance(e, ImportError) else str(e)[:60],
                    f'pip install {pipname}' + ('' if req else '   (opcional: só para recortar sujeito em capa plana)'))
    ff, fp = shutil.which('ffmpeg'), shutil.which('ffprobe')
    rep.add(bool(ff), 'ffmpeg no PATH', ff or 'não encontrado', 'Instale o FFmpeg e reabra o terminal (Windows: winget install Gyan.FFmpeg · macOS: brew install ffmpeg)')
    rep.add(bool(fp), 'ffprobe no PATH', fp or 'não encontrado', 'Vem junto com o FFmpeg')
    if ff:
        r = _run(['ffmpeg', '-hide_banner', '-encoders']); enc = r.stdout if r else ''
        rep.add('libx264' in enc, 'encoder H.264 (libx264)', '', 'Use um build do FFmpeg com libx264')
        rep.add('prores_ks' in enc or None, 'encoder ProRes (prores_ks)', '', 'Só necessário com --codec prores')
        v = _run(['ffmpeg', '-version'])
        if v and v.stdout: rep.add(True, 'versão do ffmpeg', v.stdout.splitlines()[0][:70])
    try:
        d = tempfile.mkdtemp(prefix='amstudio_Áção_')
        p = os.path.join(d, 'teste ção.png')
        ok = imwrite(p, np.zeros((8, 8, 3), np.uint8)) and os.path.getsize(p) > 0
        shutil.rmtree(d, ignore_errors=True)
        rep.add(ok, 'caminhos com acentos/espaços (E/S de imagem)')
    except Exception as e:
        rep.add(False, 'caminhos com acentos/espaços', str(e)[:80])
    enc = (sys.stdout.encoding or '').lower()
    rep.add(True if 'utf' in enc else None, 'console', enc or '?', 'Ok: o programa força UTF-8 com substituição segura')


def _synthetic_project(d, size=1024, light=False):
    from . import scene as S
    import cv2
    os.makedirs(os.path.join(d, 'assets'), exist_ok=True)
    rng = np.random.default_rng(1)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size
    base = np.stack([60 + 120 * x, 20 + 60 * y, 90 + 130 * (1 - x) * y], -1)
    img = np.clip(base + cv2.GaussianBlur(rng.normal(0, 25, (size, size, 3)).astype(np.float32), (0, 0), size / 40), 0, 255).astype(np.uint8)
    cv2.putText(img, 'DOCTOR', (int(size * .12), int(size * .35)), cv2.FONT_HERSHEY_DUPLEX, size / 180, (230, 230, 245), max(2, size // 90), cv2.LINE_AA)
    imwrite(os.path.join(d, 'source_flat.png'), img); imwrite(os.path.join(d, 'assets', 'bg.png'), img)
    layers = [{'id': 'bg', 'type': 'image', 'asset': 'assets/bg.png', 'effects': [{'type': 'flow', 'amp': 13}]},
              {'id': 'leaks', 'type': 'generator', 'effect': 'light_leaks', 'params': {}}]
    if not light:
        layers += [{'id': 'rings', 'type': 'generator', 'effect': 'rings', 'params': {'center': [900, 1300]}},
                   {'id': 'shards', 'type': 'generator', 'effect': 'shards', 'params': {'origin': [900, 1300]}},
                   {'id': 'embers', 'type': 'generator', 'effect': 'embers', 'params': {'origin': [900, 1300]}},
                   {'id': 'sparkles', 'type': 'generator', 'effect': 'sparkles', 'params': {'zones': [{'box': [200, 200, 1800, 1500], 'count': 10}]}},
                   {'id': 'vig', 'type': 'generator', 'effect': 'vignette', 'params': {}}]
    scene = {'version': 2, 'name': 'doctor', 'source': {'flat': 'source_flat.png', 'psd': None},
             'output': {'duration': 12, 'fps': 30, 'intensity': 1.0, 'key_content_y': [75, 1320]}, 'layers': layers}
    S.save(d, scene)
    return scene


def _time_render(d, scene, W, n=8):
    from .engine import Renderer
    r = Renderer(d, scene, W); r.frame(0)
    t = time.time()
    frames = [r.frame(i * 7 + 1) for i in range(n)]
    return (time.time() - t) / n, frames


def _time_encode(frames, w, h):
    from .outputs import encoder
    import cv2
    fr = [cv2.resize(f, (w, h)) if f.shape[:2] != (h, w) else f for f in frames]
    out = os.path.join(tempfile.gettempdir(), 'amstudio_bench.mov')
    t = time.time(); p = encoder(out, w, h, 30, 'h264', '80M')
    for f in fr: p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait()
    try: os.remove(out)
    except OSError: pass
    return (time.time() - t) / len(fr)


# fatores empíricos calibrados contra render REAL (ver docs/16-desempenho.md)
CAL = {'3x4': 1.1, '1x1': 1.4}
PSD_FACTOR = 2.0        # PSD real complexo (15–30 camadas, ajustes) ≈ 2× a "cena completa" de teste


def estimate_minutes(r2048, alpha, enc, W, N, init):
    return (init + N * (r2048 * (W / 2048.0) ** alpha + enc)) / 60.0


def bench(rep):
    d = tempfile.mkdtemp(prefix='amstudio_bench_')
    try:
        r1k, r2k = {}, {}
        for label, light in (('leve', True), ('completa', False)):
            sc = _synthetic_project(d, 2048, light)
            r1k[label], _ = _time_render(d, sc, 1024, 6)
            r2k[label], frames = _time_render(d, sc, 2048, 4)
        e34 = _time_encode(frames, 2048, 2732); e11 = _time_encode(frames, 3840, 3840)
        N = 360
        print('\n  Benchmark (medido nesta máquina com uma cena de teste; extrapolado — estimativa ±35%):')
        print(f'    render por quadro a 2048 px: cena leve {r2k["leve"]:.2f} s · cena completa {r2k["completa"]:.2f} s')
        print(f'    encode H.264 80 Mbps por quadro: 3:4 {e34:.2f} s · 1:1 {e11:.2f} s')
        print('\n    Estimativa para um clipe de 12 s @ 30 fps (360 quadros), tempo total por formato:')
        print(f'    {"formato / motor":<36}{"cena leve":>12}{"cena completa":>15}{"PSD complexo":>15}')
        rows = (('3:4  2048×2732', 2048, e34, '3x4'), ('1:1  3840² (motor 2048, rápido)', 2048, e11, '1x1'),
                ('1:1  3840² (motor 3000 — capa 3000)', 3000, e11, '1x1'), ('1:1  3840² (motor 3840 — capa 4K)', 3840, e11, '1x1'))
        for name, W, enc, fm in rows:
            cells = []
            for k, mult in (('leve', 1.0), ('completa', 1.0), ('completa', PSD_FACTOR)):
                alpha = min(2.3, max(1.6, math.log(max(r2k[k], 1e-4) / max(r1k[k], 1e-4)) / math.log(2)))
                m = estimate_minutes(r2k[k] * mult, alpha, enc, W, N, 5 + 12 * (W / 2048.0) ** 2) * CAL[fm]
                cells.append(f'{m * 0.8:.0f}–{m * 1.35:.0f} min')
            print(f'    {name:<36}{cells[0]:>12}{cells[1]:>15}{cells[2]:>15}')
        print('    ⚠ Estimativa. O tempo real depende da CPU, do nº de camadas/efeitos, da duração (8–35 s) e do tamanho dos arquivos.')
        rep.add(True, 'benchmark executado', f'{r2k["completa"]:.2f} s/quadro a 2048 px (cena completa)')
    finally:
        shutil.rmtree(d, ignore_errors=True)


def selftest(rep):
    from . import scene as S, outputs
    d = tempfile.mkdtemp(prefix='amstudio_self_Áção_')
    try:
        sc = _synthetic_project(d, 1024, False)
        errs, _ = S.validate(d, sc)
        rep.add(not errs, 'cena sintética válida', '; '.join(errs)[:100])
        ck = outputs.check(d, sc, W=192)
        rep.add(not ck['errors'], 'check (frame 0, loop, flash)', f'frame0={ck["metrics"].get("frame0_vs_capa")} flash={ck["metrics"].get("rajada_flash")}', '; '.join(ck['errors'])[:160])
        path = outputs.render_format(d, sc, '3x4', 'SELFTEST', os.path.join(d, 'out'), 'h264', '80M', 'auto', None, 6, log=lambda *a: None)
        pr = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,sample_aspect_ratio,codec_name,pix_fmt', '-of', 'json', path])
        v = json.loads(pr.stdout)['streams'][0] if pr and pr.stdout else {}
        rep.add((v.get('width'), v.get('height')) == (2048, 2732), 'render 3:4 (6 quadros) — dimensões', f'{v.get("width")}x{v.get("height")}')
        rep.add(v.get('sample_aspect_ratio') == '1:1', 'pixel quadrado (SAR 1:1)', str(v.get('sample_aspect_ratio')))
        rep.add(v.get('codec_name') == 'h264', 'codec H.264', f'{v.get("codec_name")} {v.get("pix_fmt")}')
    except Exception as e:
        rep.add(False, 'autoteste', f'{type(e).__name__}: {e}'[:200], 'Cole esta linha numa issue')
    finally:
        shutil.rmtree(d, ignore_errors=True)


def run(args):
    print(f'Apple Music Album Motion Art — doctor (v{__import__("amstudio").__version__})\n')
    rep = Report()
    check_env(rep)
    if args.selftest and not rep.failed:
        selftest(rep)
    rep.print()
    if args.bench and not rep.failed:
        bench(rep)
    print('\nRESULTADO:', 'PROBLEMAS ENCONTRADOS (veja os ❌ e as dicas ↳)' if rep.failed else 'AMBIENTE OK')
    return 1 if rep.failed else 0
