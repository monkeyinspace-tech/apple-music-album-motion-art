"""Saídas: extensão 3:4, encoders (H.264/ProRes), render por formato, preview, GIF e checagem automática."""
import json, math, os, subprocess, time
import cv2, numpy as np
from . import REF, scene as sc_mod
from .engine import Renderer
from .ingest import working_size
from .compat import imread, imwrite

SAFE34 = (458, 1709)       # Art Safe Area (y) do canvas 2048×2732


class Ext3x4:
    """Canvas 3:4 a partir do quadro quadrado: arte em LARGURA TOTAL; extensão só em cima/embaixo (nunca moldura)."""

    def __init__(self, cover_sq, key_y, W):
        self.W, f = W, W / REF
        self.H = int(round(2732 * f))
        y0 = int(round(((SAFE34[0] + SAFE34[1]) / 2 - (key_y[0] + key_y[1]) / 2) * f))
        self.y0 = max(0, min(y0, self.H - W))
        self.pt, self.pb = self.y0, self.H - (self.y0 + W)
        cov = cv2.resize(cover_sq, (W, W), interpolation=cv2.INTER_AREA)
        st = max(4, int(36 * f))
        lum_t = float(cov[:st].mean() / 255.0); lum_b = float(cov[W - st:].mean() / 255.0)       # capas CLARAS não devem escurecer demais
        self.top = self._ext(cov[:st], self.pt, True, 0.55 + 0.40 * lum_t, True, f)
        self.bot = self._ext(cov[W - st:][::-1], self.pb, False, 0.20 + 0.35 * lum_b, False, f)
        self.band = max(8, int(70 * f))
        ramp = np.linspace(0, 1, 2 * self.band, dtype=np.float32)
        self.sw = ((np.minimum(ramp, 1 - ramp) * 2) ** 1.5 * 0.55)[:, None, None]
        self.f = f

    def _ext(self, strip, n, flip, lo, top, f):
        if n <= 0: return np.zeros((0, self.W, 3), np.uint8)
        k, rows, i = strip.shape[0], [], 0
        while len(rows) < n:
            idx = i % (2 * k); rows.append(strip[idx if idx < k else 2 * k - 1 - idx]); i += 1
        o = np.stack(rows[:n]); o = o[::-1] if flip else o
        o = cv2.GaussianBlur(o, (0, 0), sigmaX=110 * f, sigmaY=28 * f).astype(np.float32)     # mais borrado na horizontal: sem listras verticais
        ramp = np.linspace(0, 1, n, dtype=np.float32)
        fade = (lo + (1 - lo) * ramp) if top else (1 - (1 - lo) * ramp ** 1.3)
        return (o * fade[:, None, None]).astype(np.uint8)

    def make(self, fr):
        c = np.empty((self.H, self.W, 3), np.uint8)
        c[:self.pt] = self.top; c[self.pt:self.pt + self.W] = fr; c[self.pt + self.W:] = self.bot
        for sy in [y for y in (self.pt, self.pt + self.W) if 0 < y < self.H]:
            a, b = max(sy - self.band, 0), min(sy + self.band, self.H)
            seg = c[a:b]
            if seg.shape[0] != 2 * self.band: continue
            c[a:b] = (seg * (1 - self.sw) + cv2.GaussianBlur(seg, (0, 0), 18 * self.f) * self.sw).astype(np.uint8)
        return c


def _flat(project_dir, scene):
    return imread(sc_mod.flat_path(project_dir, scene))


def encoder(path, w, h, fps, codec='h264', bitrate='80M', container='mov'):
    vf = 'scale=out_color_matrix=bt709:out_range=tv,' + ('format=yuv422p10le' if codec == 'prores' else 'format=yuv420p') + ',setsar=1'
    base = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{w}x{h}', '-r', str(fps), '-i', '-', '-an', '-vf', vf]
    if codec == 'prores':
        c = ['-c:v', 'prores_ks', '-profile:v', '2', '-vendor', 'apl0']
    else:
        c = ['-c:v', 'libx264', '-profile:v', 'high', '-preset', 'medium', '-tag:v', 'avc1', '-b:v', bitrate, '-minrate', bitrate,
             '-maxrate', '95M', '-bufsize', '140M', '-g', str(fps), '-x264-params', 'force-cfr=1:rc-lookahead=10:threads=2']
    tail = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart', '-f', container, path]
    return subprocess.Popen(base + c + tail, stdin=subprocess.PIPE)


def render_format(project_dir, scene, fmt, upc, outdir, codec='h264', bitrate='80M', work='auto', intensity=None, test_frames=0, log=print,
                  container='mov', static=False):
    out = scene.get('output', {})
    fps = out.get('fps', 30)
    flat = _flat(project_dir, scene)
    W = REF if fmt == '3x4' else working_size(flat.shape[0], work)
    r = Renderer(project_dir, scene, W, intensity)
    os.makedirs(outdir, exist_ok=True)
    if codec == 'prores': container = 'mov'                    # ProRes só existe em MOV
    path = os.path.join(outdir, f'{upc}_{fmt}.{container}')
    if fmt == '3x4':
        ext = Ext3x4(r.ctx.cover, out.get('key_content_y', [75, 1320]), W)
        pp = encoder(path, W, ext.H, fps, codec, bitrate, container)
        conv = ext.make
        log(f'[{fmt}] canvas {W}x{ext.H} · conteúdo-chave y={out.get("key_content_y", [75, 1320])} → Y0={ext.y0}')
    else:
        pp = encoder(path, 3840, 3840, fps, codec, bitrate, container)
        conv = (lambda fr: fr) if W == 3840 else (lambda fr: cv2.resize(fr, (3840, 3840), interpolation=cv2.INTER_CUBIC))
        log(f'[{fmt}] motor em {W}px' + ('' if W == 3840 else f' → ampliado para 3840 (capa-fonte {flat.shape[0]}px)'))
    t0 = time.time()
    n = test_frames or r.N
    for f in range(n):
        img = conv(r.frame(f))
        if static and f == 0:                                    # PNG estático = frame 0 (== capa); alguns distribuidores o exigem
            imwrite(os.path.join(outdir, f'{upc}_{fmt}_static.png'), img)
        pp.stdin.write(img.tobytes())
        if f % 30 == 0: log(f'[{fmt}] frame {f}/{r.N}  {time.time() - t0:.0f}s')
    pp.stdin.close(); pp.wait()
    log(f'DONE {fmt} -> {path}')
    return path


def contact_sheet(project_dir, scene, path, W=768, times=(0, 1 / 6, 1 / 3, 1 / 2, 2 / 3, 5 / 6), intensity=None, fmt='3x4'):
    r = Renderer(project_dir, scene, W, intensity)
    ext = Ext3x4(r.ctx.cover, scene.get('output', {}).get('key_content_y', [75, 1320]), W) if fmt == '3x4' else None
    tiles = []
    for t in times:
        fr = r.frame(int(round(t * r.N)))
        im = ext.make(fr) if ext else fr
        tiles.append(cv2.resize(im, (456, int(456 * im.shape[0] / im.shape[1])), interpolation=cv2.INTER_AREA))
    rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3) if len(tiles[i:i + 3]) == 3]
    imwrite(path, np.vstack(rows))
    return path


def stills(project_dir, scene, outdir, ts, W=1024, intensity=None, fmt='3x4'):
    r = Renderer(project_dir, scene, W, intensity)
    ext = Ext3x4(r.ctx.cover, scene.get('output', {}).get('key_content_y', [75, 1320]), W) if fmt == '3x4' else None
    os.makedirs(outdir, exist_ok=True); paths = []
    for t in ts:
        fr = r.frame(int(round(t * r.N)))
        p = os.path.join(outdir, f'frame_t{int(round(t * 100)):03d}.png')
        imwrite(p, ext.make(fr) if ext else fr); paths.append(p)
    return paths


def make_gif(project_dir, scene, path, intensity=None, gw=360, step=2):
    r = Renderer(project_dir, scene, 1024, intensity)
    ext = Ext3x4(r.ctx.cover, scene.get('output', {}).get('key_content_y', [75, 1320]), 1024)
    gh = int(gw * ext.H / ext.W)
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{gw}x{gh}', '-r', str(r.ctx.fps // step), '-i', '-',
           '-vf', 'split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5', '-loop', '0', path]
    pg = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(0, r.N, step):
        pg.stdin.write(cv2.resize(ext.make(r.frame(f)), (gw, gh), interpolation=cv2.INTER_AREA).tobytes())
    pg.stdin.close(); pg.wait()
    return path


def _flash(mean_luma, fps):
    d = np.diff(mean_luma)
    big = np.where(np.abs(d) > 0.10)[0]
    worst = max([int(((big >= i) & (big < i + fps)).sum()) for i in big] + [0])
    return (float(np.abs(d).max()) if len(d) else 0.0), worst


def check(project_dir, scene, W=320, intensity=None):
    """Validação da cena + render rápido (320 px) de TODOS os quadros: frame 0, loop, flash, estouro."""
    rep = {'errors': [], 'warnings': [], 'metrics': {}}
    errs, warns = sc_mod.validate(project_dir, scene)
    rep['errors'], rep['warnings'] = errs, warns
    if errs: return rep
    r = Renderer(project_dir, scene, W, intensity)
    flat = cv2.resize(_flat(project_dir, scene), (W, W), interpolation=cv2.INTER_AREA)
    frames = [cv2.cvtColor(r.frame(f), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255 for f in range(r.N)]
    f0 = r.frame(0)
    m = rep['metrics']
    bl = lambda x: cv2.GaussianBlur(x.astype(np.float32), (0, 0), 1.5)       # ignora diferenças de antialiasing nas bordas das camadas
    m['frame0_vs_capa'] = round(float(np.abs(bl(f0) - bl(flat)).mean()), 3)
    cons = np.array([np.abs(frames[i + 1] - frames[i]).mean() for i in range(len(frames) - 1)])
    wrap = float(np.abs(frames[0] - frames[-1]).mean())
    m['salto_fechamento'], m['salto_tipico'] = round(wrap, 5), round(float(np.median(cons)), 5)
    mean = np.array([f.mean() for f in frames])
    m['max_salto_luminancia_pct'], m['rajada_flash'] = [round(v * 100 if i == 0 else v, 2) for i, v in enumerate(_flash(mean, r.ctx.fps))]
    m['luminancia_max_vs_f0'] = round(float(mean.max() / max(mean[0], 1e-3)), 2)
    limit = 6.0 if (scene.get('source') or {}).get('psd') else 1.5          # PSD aproxima ajustes/efeitos; capa plana não tem desculpa
    if m['frame0_vs_capa'] > limit:
        rep['errors'].append(f'frame 0 difere da capa ({m["frame0_vs_capa"]}/255): algum efeito não começa em zero ou o recorte/PSD está errado')
    elif m['frame0_vs_capa'] > 1.5:
        rep['warnings'].append(f'frame 0 difere levemente da capa ({m["frame0_vs_capa"]}/255): em PSDs é esperado (ajustes/efeitos/smart objects aproximados). '
                               'Compare lado a lado; se for visível, rasterize os ajustes no PSD')
    if wrap > max(3 * m['salto_tipico'], 0.01):
        rep['warnings'].append('o fechamento do loop tem um salto maior que o normal (algum efeito não fecha em zero)')
    if scene.get('output', {}).get('duration', 12) < 15:
        rep['warnings'].append('duração < 15 s: o toolkit oficial aceita 8–35 s, mas algumas distribuidoras exigem 15–35 s — confirme com a sua')
    if m['rajada_flash'] > 3:
        rep['errors'].append('risco de flash/strobe (>3 transições >10% de luminância em 1 s)')
    if m['luminancia_max_vs_f0'] > 1.6:
        rep['warnings'].append(f'a luminância média chega a {m["luminancia_max_vs_f0"]}× a do frame 0: possível brilho estourado no meio do loop (veja o preview!)')
    return rep
