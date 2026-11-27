"""Motor de composição: camadas (imagem, texto, gerador, trava) + keyframes + efeitos + blend modes.

Convenções
- Todas as coordenadas do scene.json estão no espaço de referência 2048×2048 (REF). O motor converte
  para o tamanho de trabalho W (2048 … 3840) com `ctx.sc = W / 2048`, então a MESMA cena serve para
  capas de 2048, 3000, 3840 ou 4096 px.
- Camadas são compostas de baixo (primeira da lista) para cima (última).
- Pixels de camada ficam em float32 BGR *pré-multiplicado* + alfa (H×W×4).
"""
import math, os
import cv2, numpy as np
from . import REF, fx
from .curves import evaluate
from .compat import imread

BLEND_MODES = ('normal', 'add', 'screen', 'multiply', 'lighten')
TAU = 2 * math.pi


class Ctx:
    def __init__(self, W, fps, duration, intensity, cover):
        self.W, self.sc = W, W / REF
        self.fps, self.dur, self.N = fps, duration, int(round(fps * duration))
        self.K = float(intensity)
        self.cover = cover               # BGR uint8 W×W (capa achatada)
        self.layers = {}


def _find_font(name=None):
    cands = [name] if name else []
    cands += ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf', 'C:/Windows/Fonts/impact.ttf',
              '/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/Library/Fonts/Arial Bold.ttf',
              '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf']
    return next((c for c in cands if c and os.path.exists(c)), None)


def _hex_to_bgr(c):
    if isinstance(c, str):
        c = c.lstrip('#')
        return (int(c[4:6], 16), int(c[2:4], 16), int(c[0:2], 16))
    return tuple(int(v) for v in c)


def _blend(dst, P, a, mode):
    """dst: float32 (h,w,3) 0..255 (modificado no lugar); P: BGR pré-multiplicado; a: (h,w,1) alfa final."""
    if mode == 'normal':
        dst *= (1 - a); dst += P
    elif mode == 'add':
        dst += P
    elif mode == 'screen':
        dst += P * (1 - dst / 255.0)
    elif mode == 'multiply':
        dst *= (1 - a) + P / 255.0
    elif mode == 'lighten':
        np.maximum(dst, P + dst * (1 - a), out=dst)


class ImageLayer:
    kind = 'image'

    def __init__(self, ctx, spec, base_dir, rgba=None):
        self.id, self.spec, self.ctx = spec['id'], spec, ctx
        sc, W = ctx.sc, ctx.W
        bb = spec.get('bbox') or [0, 0, REF, REF]
        self.ref_bbox = bb
        self.ref_w, self.ref_h = bb[2] - bb[0], bb[3] - bb[1]
        ax0, ay0, ax1, ay1 = [int(round(v * sc)) for v in bb]
        if rgba is None:
            path = os.path.join(base_dir, spec['asset'])
            img = imread(path, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise FileNotFoundError(f'camada "{self.id}": asset não encontrado: {path}')
            if img.dtype == np.uint16: img = (img / 257).astype(np.uint8)
            if img.ndim == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            if img.shape[2] == 3: img = np.dstack([img, np.full(img.shape[:2], 255, np.uint8)])
        else:
            img = rgba
        tw, th = max(1, ax1 - ax0), max(1, ay1 - ay0)
        if (img.shape[1], img.shape[0]) != (tw, th):
            img = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA if tw < img.shape[1] else cv2.INTER_CUBIC)
        # recorta ao canvas
        cx0, cy0, cx1, cy1 = max(ax0, 0), max(ay0, 0), min(ax1, W), min(ay1, W)
        if cx1 <= cx0 or cy1 <= cy0:
            raise ValueError(f'camada "{self.id}" está totalmente fora do canvas')
        img = img[cy0 - ay0:cy1 - ay0, cx0 - ax0:cx1 - ax0]
        a = img[..., 3:4].astype(np.float32) / 255.0
        P = img[..., :3].astype(np.float32) * a
        m = int(spec.get('margin', 60) * sc)
        ex0, ey0 = (cx0 - m if cx0 > 0 else cx0), (cy0 - m if cy0 > 0 else cy0)
        ex1, ey1 = (cx1 + m if cx1 < W else cx1), (cy1 + m if cy1 < W else cy1)
        ex0, ey0, ex1, ey1 = max(ex0, 0), max(ey0, 0), min(ex1, W), min(ey1, W)
        self.x0, self.y0, self.w, self.h = ex0, ey0, ex1 - ex0, ey1 - ey0
        self.base = np.zeros((self.h, self.w, 4), np.float32)
        self.base[cy0 - ey0:cy1 - ey0, cx0 - ex0:cx1 - ex0, :3] = P
        self.base[cy0 - ey0:cy1 - ey0, cx0 - ex0:cx1 - ex0, 3:] = a
        pv = spec.get('pivot') or [(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2]
        self.pivot = (pv[0] * sc - self.x0, pv[1] * sc - self.y0)
        self.blend = spec.get('blend', 'normal')
        self.opacity = float(spec.get('opacity', 1.0))
        self.visible = spec.get('visible', True)
        self.tr = spec.get('transform', {}) or {}
        self.fxs = []
        self._calpha = None

    def build_effects(self):
        for e in self.spec.get('effects', []) or []:
            params = {k: v for k, v in e.items() if k not in ('type', 'enabled')}
            if e.get('enabled', True):
                self.fxs.append(fx.LAYER[e['type']](self.ctx, self, **params))

    def canvas_alpha(self):
        if self._calpha is None:
            W = self.ctx.W
            c = np.zeros((W, W), np.float32)
            c[self.y0:self.y0 + self.h, self.x0:self.x0 + self.w] = self.base[..., 3]
            self._calpha = c
        return self._calpha

    def render(self, fr, t, e):
        if not self.visible: return
        K, sc = self.ctx.K, self.ctx.sc
        img = self.base
        for f in self.fxs:
            img = f.apply(img, t, e)
        tx = evaluate(self.tr.get('x', 0), t) * sc * K
        ty = evaluate(self.tr.get('y', 0), t) * sc * K
        rot = math.radians(evaluate(self.tr.get('rotation', 0), t) * K)
        s = 1 + (evaluate(self.tr.get('scale', 1), t) - 1) * K
        op = self.opacity * evaluate(self.tr.get('opacity', 1), t)
        if abs(tx) + abs(ty) + abs(rot) + abs(s - 1) > 1e-6:
            cx, cy = self.pivot
            cs, sn = math.cos(rot) * s, math.sin(rot) * s
            M = np.array([[cs, -sn, cx - cs * cx + sn * cy + tx], [sn, cs, cy - sn * cx - cs * cy + ty]], np.float32)
            img = cv2.warpAffine(img, M, (self.w, self.h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        roi = fr[self.y0:self.y0 + self.h, self.x0:self.x0 + self.w]
        a = img[..., 3:4] * op
        _blend(roi, img[..., :3] * op, a, self.blend)


class TextLayer(ImageLayer):
    """Texto vira uma imagem RGBA (via Pillow) e se comporta como qualquer camada de imagem."""
    kind = 'text'

    def __init__(self, ctx, spec, base_dir):
        from PIL import Image, ImageDraw, ImageFont
        size = int(spec.get('size', 160))
        font_path = _find_font(spec.get('font'))
        font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        txt = spec['text']
        probe = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
        l, t_, r, b = probe.multiline_textbbox((0, 0), txt, font=font, align=spec.get('align', 'center'))
        pad = int(size * 0.3)
        im = Image.new('RGBA', (r - l + 2 * pad, b - t_ + 2 * pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        col = _hex_to_bgr(spec.get('color', '#ffffff'))
        stroke = spec.get('stroke')
        d.multiline_text((pad - l, pad - t_), txt, font=font, fill=(col[2], col[1], col[0], 255), align=spec.get('align', 'center'),
                         stroke_width=int(spec.get('stroke_width', 0)), stroke_fill=tuple(_hex_to_bgr(stroke)[::-1]) + (255,) if stroke else None)
        arr = np.array(im)                      # RGBA
        bgra = arr[..., [2, 1, 0, 3]].copy()
        cx, cy = spec.get('position', [REF / 2, REF / 2])
        w_ref, h_ref = bgra.shape[1], bgra.shape[0]
        spec = dict(spec)
        spec['bbox'] = [cx - w_ref / 2, cy - h_ref / 2, cx + w_ref / 2, cy + h_ref / 2]
        # o PNG foi desenhado em px de referência (2048); o ImageLayer reamostra para o tamanho de trabalho
        super().__init__(ctx, spec, base_dir, rgba=bgra)


class GeneratorLayer:
    kind = 'generator'

    def __init__(self, ctx, spec):
        self.id, self.spec = spec['id'], spec
        self.visible = spec.get('visible', True)
        self.inst = fx.GEN[spec['effect']](ctx, **(spec.get('params') or {}))

    def link(self, ctx, layers):
        if hasattr(self.inst, 'link'): self.inst.link(ctx, layers)

    def render(self, fr, t, e):
        if self.visible: self.inst.render(fr, t, e)


class LockLayer:
    """Restaura regiões da capa original em todo quadro (logos, texto legal, créditos)."""
    kind = 'lock'

    def __init__(self, ctx, spec):
        self.id, self.visible, self.ctx = spec['id'], spec.get('visible', True), ctx
        sc, W = ctx.sc, ctx.W
        self.items = []
        for (x0, y0, x1, y1) in spec['boxes']:
            m = np.zeros((W, W), np.float32)
            m[int((y0 + 30) * sc):int((y1 - 30) * sc), int((x0 + 20) * sc):int((x1 - 20) * sc)] = 1
            sl = (slice(max(int(y0 * sc), 0), min(int(y1 * sc), W)), slice(max(int(x0 * sc), 0), min(int(x1 * sc), W)))
            self.items.append((sl, cv2.GaussianBlur(m, (0, 0), 6 * sc)[sl][..., None]))
        self.cov = ctx.cover.astype(np.float32)

    def render(self, fr, t, e):
        if not self.visible: return
        for sl, w in self.items:
            fr[sl] = fr[sl] * (1 - w) + self.cov[sl] * w


class AdjustLayer:
    """Camada de ajuste (como no Photoshop): aplica uma curva de cor por canal e/ou uma correção suave a TUDO que está abaixo dela.
    Usada pelo importador de PSD para aproximar Curves / Brightness-Contrast / Hue-Saturation e efeitos que o motor não replica.
    Estático: não muda com o tempo (não mexe no frame 0 == capa)."""
    kind = 'adjust'

    def __init__(self, ctx, spec, base_dir):
        import json
        self.id, self.visible = spec['id'], spec.get('visible', True)
        self.strength = float(spec.get('strength', 1.0))
        self.lut = None
        if spec.get('lut'):
            d = json.load(open(os.path.join(base_dir, spec['lut']), encoding='utf-8'))
            self.lut = np.stack([np.array(d[c], np.float32) for c in ('b', 'g', 'r')], axis=-1).reshape(1, 256, 3)
        self.res = None
        if spec.get('residual'):
            r = imread(os.path.join(base_dir, spec['residual']))
            if r is not None:
                self.res = cv2.resize(r, (ctx.W, ctx.W), interpolation=cv2.INTER_CUBIC).astype(np.float32) - 128.0

    def render(self, fr, t, e):
        if not self.visible: return
        if self.lut is not None:
            u8 = np.clip(fr, 0, 255).astype(np.uint8)
            graded = cv2.LUT(u8, np.clip(self.lut, 0, 255).astype(np.uint8)).astype(np.float32)
            fr[:] = graded if self.strength >= 1 else fr * (1 - self.strength) + graded * self.strength
        if self.res is not None:
            fr += self.res * self.strength


class Renderer:
    def __init__(self, project_dir, scene, W=2048, intensity=None, plugin_dirs=()):
        from .scene import flat_path
        fx.load_plugins(os.path.join(project_dir, 'plugins'), *plugin_dirs)
        out = scene.get('output', {})
        fps, dur = out.get('fps', 30), out.get('duration', 12)
        K = out.get('intensity', 1.0) if intensity is None else intensity
        cover = imread(flat_path(project_dir, scene))
        if cover is None:
            raise FileNotFoundError('capa achatada (source_flat.png) não encontrada no projeto')
        cover = cv2.resize(cover, (W, W), interpolation=cv2.INTER_AREA if cover.shape[0] > W else cv2.INTER_CUBIC)
        self.ctx = ctx = Ctx(W, fps, dur, K, cover)
        self.layers = []
        for spec in scene['layers']:
            ty = spec['type']
            if ty == 'image': L = ImageLayer(ctx, spec, project_dir)
            elif ty == 'text': L = TextLayer(ctx, spec, project_dir)
            elif ty == 'generator': L = GeneratorLayer(ctx, spec)
            elif ty == 'lock': L = LockLayer(ctx, spec)
            elif ty == 'adjust': L = AdjustLayer(ctx, spec, project_dir)
            else: raise ValueError(f'tipo de camada desconhecido: {ty}')
            ctx.layers[L.id] = L
            self.layers.append(L)
        for L in self.layers:                      # efeitos de camada só depois de TODAS existirem (link entre camadas)
            if isinstance(L, ImageLayer): L.build_effects()
        for L in self.layers:
            if isinstance(L, GeneratorLayer): L.link(ctx, ctx.layers)
            if isinstance(L, ImageLayer):
                for f in L.fxs:
                    if hasattr(f, 'link'): f.link(ctx, ctx.layers)

    @property
    def N(self): return self.ctx.N

    def frame(self, f):
        t = (f % self.ctx.N) / self.ctx.N
        e = (1 - math.cos(TAU * t)) / 2
        fr = np.zeros((self.ctx.W, self.ctx.W, 3), np.float32)
        for L in self.layers:
            L.render(fr, t, e)
        return np.clip(fr, 0, 255).astype(np.uint8)
