"""GERADORES embutidos: desenham direto no quadro (float32 BGR 0..255)."""
import math
import cv2, numpy as np
from . import generator
from .util import ell, odd, palette

TAU = 2 * math.pi


def _clip(fr, cx, cy, w, h):
    H, W = fr.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    return x0, y0, max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)


def blend_patch(fr, bgr, a, cx, cy):
    h, w = a.shape
    x0, y0, X0, Y0, X1, Y1 = _clip(fr, cx, cy, w, h)
    if X1 <= X0 or Y1 <= Y0: return
    sa = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, None]
    fr[Y0:Y1, X0:X1] = fr[Y0:Y1, X0:X1] * (1 - sa) + bgr[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * sa


def add_patch(fr, bgr, cx, cy):
    h, w = bgr.shape[:2]
    x0, y0, X0, Y0, X1, Y1 = _clip(fr, cx, cy, w, h)
    if X1 <= X0 or Y1 <= Y0: return
    fr[Y0:Y1, X0:X1] += bgr[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]


@generator('light_leaks', {
    'colors': ('list', None, '[[B,G,R],[B,G,R]]; omitido = cores vivas extraídas da própria capa'),
    'amp1': ('float', 0.10, 'intensidade do 1º vazamento'), 'amp2': ('float', 0.08, 'intensidade do 2º'),
}, 'Dois blobs de luz coloridos que passeiam atrás do conteúdo (clima/atmosfera).')
class LightLeaks:
    def __init__(self, ctx, colors=None, amp1=0.10, amp2=0.08):
        self.W, self.K = ctx.W, ctx.K
        self.c1, self.c2 = (colors[0], colors[1]) if colors else palette(ctx.cover)
        self.a1, self.a2 = amp1, amp2
        g = max(32, ctx.W // 8)
        self.g = g
        self.bx, self.by = np.meshgrid(np.arange(g, dtype=np.float32), np.arange(g, dtype=np.float32))

    def _blob(self, cx, cy, r, color, amp):
        k = self.g / self.W
        d = ((self.bx - cx * k) ** 2 + (self.by - cy * k) ** 2) / (r * k) ** 2
        return np.exp(-d)[..., None] * np.array(color, np.float32) * amp

    def render(self, fr, t, e):
        a, S = TAU * t, self.W
        g = self._blob(S * (0.72 + 0.12 * math.sin(a)), S * (0.45 + 0.10 * math.sin(2 * a + 1)), S * 0.30, self.c1, self.a1 * e * self.K)
        g += self._blob(S * (0.28 - 0.10 * math.sin(a + 0.8)), S * (0.66 + 0.08 * math.cos(a)), S * 0.26, self.c2, self.a2 * e * self.K)
        fr += cv2.resize(g, (S, S), interpolation=cv2.INTER_LINEAR)


@generator('rings', {
    'center': ('point', None, '[x,y] origem das ondas (espaço 2048)'), 'count': ('int', 3, 'ondas por loop'),
    'max_radius': ('float', 720, 'raio máximo (px)'), 'strength': ('float', 0.30, 'intensidade'),
    'color': ('color', [210, 120, 255], 'cor BGR'),
}, 'Ondas de choque suaves expandindo de um ponto (impacto, batida, pulso).')
class Rings:
    def __init__(self, ctx, center, count=3, max_radius=720, strength=0.30, color=(210, 120, 255)):
        sc, W = ctx.sc, ctx.W
        self.cx, self.cy, self.R = center[0] * sc, center[1] * sc, max_radius * sc
        self.count, self.strength, self.color, self.K, self.sc = count, strength, np.array(color, np.float32), ctx.K, sc
        m = self.R + 100 * sc
        self.x0, self.x1 = int(max(0, self.cx - m)), int(min(W, self.cx + m))
        self.y0, self.y1 = int(max(0, self.cy - m)), int(min(W, self.cy + m))
        gx, gy = np.meshgrid(np.arange(self.x0, self.x1, dtype=np.float32), np.arange(self.y0, self.y1, dtype=np.float32))
        self.d = np.hypot(gx - self.cx, gy - self.cy)

    def render(self, fr, t, e):
        ring = np.zeros_like(self.d)
        for k in range(self.count):
            u = (t * self.count + k / self.count) % 1.0
            ring += np.exp(-((self.d - (40 * self.sc + self.R * u)) / ((14 + 40 * u) * self.sc)) ** 2) * math.sin(math.pi * u) ** 1.2 * e * min(self.K, 1.3)
        fr[self.y0:self.y1, self.x0:self.x1] += ring[..., None] * self.color * self.strength


@generator('hot_pulse', {
    'roi': ('box', None, '[x0,y0,x1,y1] região onde buscar pixels laranja/amarelos "quentes" (lava, brasa, neon)'),
    'pulses': ('int', 3, 'pulsos por loop'), 'strength': ('float', 0.42, 'intensidade'),
    'exclude_layers': ('list', None, 'ids de camadas a excluir (ex.: ["subject"])'),
}, 'Faz as áreas quentes da arte (trincas de lava, brasas, neon laranja) pulsarem como se respirassem.')
class HotPulse:
    def __init__(self, ctx, roi, pulses=3, strength=0.42, exclude_layers=None):
        self.ctx, self.roi, self.pulses, self.s, self.excl = ctx, roi, pulses, strength * ctx.K, exclude_layers or []
        self.glow = None

    def link(self, ctx, layers):
        sc, W = ctx.sc, ctx.W
        pad = int(130 * sc)
        x0, y0, x1, y1 = [int(v * sc) for v in self.roi]
        X0, Y0, X1, Y1 = max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, W), min(y1 + pad, W)
        cov = ctx.cover[Y0:Y1, X0:X1]
        hsv = cv2.cvtColor(cov, cv2.COLOR_BGR2HSV).astype(np.float32)
        hot = ((hsv[..., 0] >= 3) & (hsv[..., 0] <= 28) & (hsv[..., 1] / 255 > 0.45) & (hsv[..., 2] / 255 > 0.62)).astype(np.float32)
        inner = np.zeros_like(hot); inner[max(y0 - Y0, 0):y1 - Y0, max(x0 - X0, 0):x1 - X0] = 1
        hot *= inner
        for lid in self.excl:
            al = layers[lid].canvas_alpha()[Y0:Y1, X0:X1]
            hot *= 1 - np.clip(cv2.dilate(al, ell(15 * sc)), 0, 1)
        c = cov.astype(np.float32) * hot[..., None]
        self.glow = cv2.GaussianBlur(c, (0, 0), 14 * sc) + cv2.GaussianBlur(c, (0, 0), 40 * sc) * 0.8
        self.box = (X0, Y0, X1, Y1)

    def render(self, fr, t, e):
        X0, Y0, X1, Y1 = self.box
        fr[Y0:Y1, X0:X1] += self.glow * (self.s * (1 - math.cos(TAU * self.pulses * t)) / 2)


@generator('embers', {
    'origin': ('point', None, '[x,y] de onde saem as brasas'), 'count': ('int', 130, 'quantidade'),
    'spread': ('float', 760, 'alcance máximo (px)'), 'seed': ('int', 3, 'semente'),
}, 'Brasas/faíscas subindo de um ponto, com brilho. Nascem e morrem em zero.')
class Embers:
    def __init__(self, ctx, origin, count=130, spread=760, seed=3):
        r = np.random.default_rng(seed)
        n = int(count * ctx.K)
        self.n, self.sc, self.o = n, ctx.sc, (origin[0] * ctx.sc, origin[1] * ctx.sc)
        self.ang = r.uniform(math.radians(-178), math.radians(-2), n); self.dist = r.uniform(160, spread, n) * ctx.sc
        self.ph = r.uniform(0, 1, n); self.rad = r.uniform(1.8, 4.6, n) * ctx.sc; self.wob = r.uniform(0, 6.28, n); self.spd = r.integers(1, 3, n)
        self.pw, self.ph_ = int(1500 * ctx.sc), int(900 * ctx.sc)
        self.ox, self.oy = max(0, self.o[0] - 650 * ctx.sc), max(0, self.o[1] - 625 * ctx.sc)

    def render(self, fr, t, e):
        L = np.zeros((self.ph_, self.pw, 3), np.float32); sc = self.sc
        for i in range(self.n):
            u = (t * self.spd[i] + self.ph[i]) % 1.0
            env = math.sin(math.pi * u) ** 1.5
            if env < 0.03: continue
            x = self.o[0] + math.cos(self.ang[i]) * self.dist[i] * u + 16 * sc * math.sin(self.wob[i] + TAU * u) - self.ox
            y = self.o[1] + math.sin(self.ang[i]) * self.dist[i] * u - 90 * sc * u - self.oy
            if not (0 <= x < self.pw and 0 <= y < self.ph_): continue
            v = 255 * env * 0.9 * e
            cv2.circle(L, (int(x), int(y)), max(1, int(self.rad[i] * (1 - 0.4 * u))), (v * 0.25, v * 0.62, v), -1, cv2.LINE_AA)
        L += cv2.GaussianBlur(L, (0, 0), 5 * sc) * 1.6
        add_patch(fr, L, self.ox + self.pw / 2, self.oy + self.ph_ / 2)


@generator('shards', {
    'origin': ('point', None, '[x,y] do impacto'), 'count': ('int', 26, 'quantidade'), 'seed': ('int', 4, 'semente'),
    'rim': ('color', [120, 90, 255], 'cor BGR da borda'),
}, 'Estilhaços/pedaços escuros em trajetória balística com borda luminosa (explosão, quebra).')
class Shards:
    def __init__(self, ctx, origin, count=26, seed=4, rim=(120, 90, 255)):
        r = np.random.default_rng(seed); n = int(count * ctx.K)
        sc = ctx.sc
        self.n, self.sc, self.K, self.rim = n, sc, ctx.K, np.array(rim, np.float32)
        self.o = (origin[0] * sc, origin[1] * sc)
        self.ang = r.uniform(math.radians(-170), math.radians(-12), n); self.dist = r.uniform(300, 900, n) * sc
        self.ph = r.uniform(0, 1, n); self.r = r.uniform(14, 46, n) * sc; self.rot = r.uniform(-2.5, 2.5, n)
        self.nv = r.integers(5, 8, n); self.jit = [r.uniform(0.55, 1.0, int(k)) for k in self.nv]; self.off = r.uniform(-110, 110, (n, 2)) * sc

    def render(self, fr, t, e):
        sc = self.sc
        for i in range(self.n):
            u = (t + self.ph[i]) % 1.0
            env = math.sin(math.pi * u) ** 0.8 * e ** 0.6
            if env < 0.03: continue
            cx = self.o[0] + self.off[i, 0] + math.cos(self.ang[i]) * self.dist[i] * u
            cy = self.o[1] + self.off[i, 1] + math.sin(self.ang[i]) * self.dist[i] * u + 520 * sc * u * u
            r = self.r[i] * (0.8 + 0.5 * u); P = int(r * 2.6) | 1
            a0 = self.rot[i] * u * 3 + i
            pts = np.array([[P / 2 + math.cos(a0 + j * TAU / self.nv[i]) * r * self.jit[i][j], P / 2 + math.sin(a0 + j * TAU / self.nv[i]) * r * self.jit[i][j]]
                            for j in range(self.nv[i])], np.float32)
            m8 = np.zeros((P, P), np.uint8); cv2.fillConvexPoly(m8, (pts * 16).astype(np.int32), 255, cv2.LINE_AA, 4)
            rim = np.zeros((P, P), np.uint8); cv2.polylines(rim, [(pts * 16).astype(np.int32)], True, 255, max(1, int(2 * sc)), cv2.LINE_AA, 4)
            patch = np.full((P, P, 3), (38, 30, 44), np.float32) + rim[..., None].astype(np.float32) / 255 * self.rim * 0.8
            blend_patch(fr, patch, m8.astype(np.float32) / 255 * env * 0.92, cx, cy)


@generator('sparkles', {
    'zones': ('list', None, '[{"box":[x0,y0,x1,y1],"count":n}] onde surgem os brilhos'),
    'seed': ('int', 5, 'semente'), 'color': ('color', [255, 235, 255], 'cor BGR'),
}, 'Estrelas de 4 pontas que surgem e somem suavemente (~2,6 s), nunca piscando.')
class Sparkles:
    def __init__(self, ctx, zones, seed=5, color=(255, 235, 255)):
        r = np.random.default_rng(seed); sc = ctx.sc
        self.sp = []
        for z in zones or []:
            x0, y0, x1, y1 = z['box']
            for _ in range(int(z['count'] * min(ctx.K, 1.3))):
                self.sp.append(((r.uniform(x0, x1) * sc, r.uniform(y0, y1) * sc), r.uniform(0, 1), r.uniform(26, 58) * sc))
        self.sc, self.color = sc, tuple(int(c) for c in color)

    def render(self, fr, t, e):
        sc = self.sc
        for (p, ph, sz) in self.sp:
            u = (t + ph) % 1.0
            if u > 0.22: continue
            env = math.sin(math.pi * u / 0.22) ** 2 * e ** 0.5
            P = int(sz * 3) | 1; sp = np.zeros((P, P, 3), np.uint8); c0 = P // 2; th = max(1, int(2 * sc))
            cv2.line(sp, (c0 - int(sz), c0), (c0 + int(sz), c0), self.color, th, cv2.LINE_AA)
            cv2.line(sp, (c0, c0 - int(sz)), (c0, c0 + int(sz)), self.color, th, cv2.LINE_AA)
            cv2.circle(sp, (c0, c0), max(2, int(4 * sc)), (255, 255, 255), -1, cv2.LINE_AA)
            spf = sp.astype(np.float32); spf += cv2.GaussianBlur(spf, (0, 0), 6 * sc) * 1.2
            add_patch(fr, spf * (0.85 * env), p[0], p[1])


@generator('vignette', {'strength': ('float', 0.35, 'escurecimento máximo das bordas (0..1)')},
           'Vinheta que respira: as bordas escurecem de leve e voltam (foco no centro).')
class Vignette:
    def __init__(self, ctx, strength=0.35):
        g = 256
        y, x = np.mgrid[0:g, 0:g].astype(np.float32) / (g - 1) * 2 - 1
        m = np.clip((np.hypot(x, y) - 0.55) / 0.9, 0, 1) ** 1.5
        self.m = cv2.resize(m, (ctx.W, ctx.W), interpolation=cv2.INTER_CUBIC)[..., None]
        self.s = strength * min(ctx.K, 1.3)

    def render(self, fr, t, e):
        fr *= 1 - self.s * e * self.m


@generator('light_sweep', {
    'strength': ('float', 0.14, 'intensidade'), 'width': ('float', 300, 'largura da faixa (px)'),
    'slope': ('float', 0.6, 'inclinação'), 'color': ('color', [255, 235, 255], 'cor BGR'),
}, 'Faixa de luz suave varrendo o quadro todo uma vez por loop (reflexo de holofote/vidro).')
class LightSweep:
    def __init__(self, ctx, strength=0.14, width=300, slope=0.6, color=(255, 235, 255)):
        sc = ctx.sc
        xr = np.arange(ctx.W, dtype=np.float32) / sc; yr = np.arange(ctx.W, dtype=np.float32) / sc
        self.U = xr[None, :] + slope * yr[:, None]
        self.width, self.slope = width, slope
        self.s, self.color = strength * min(ctx.K, 1.3), np.array(color, np.float32)

    def render(self, fr, t, e):
        span = 2048 * (1 + self.slope) + 4 * self.width
        c = -2 * self.width + t * span
        fr += (np.exp(-((self.U - c) / self.width) ** 2) * self.s)[..., None] * self.color


@generator('grain', {'amount': ('float', 4.0, 'intensidade do grão de filme (níveis 0..255)')},
           'Grão de filme sutil (sobe e desce com o loop; zero nas pontas).')
class Grain:
    def __init__(self, ctx, amount=4.0):
        self.W, self.a, self.r = ctx.W, amount * ctx.K, np.random.default_rng(9)

    def render(self, fr, t, e):
        fr += self.r.normal(0, self.a * e, (self.W, self.W, 1)).astype(np.float32)


@generator('color_wash', {'color': ('color', [200, 70, 255], 'cor BGR'), 'strength': ('float', 0.12, 'intensidade')},
           'Banho de cor que sobe e desce (clima: quente, frio, neon) — modo "screen", sem estourar.')
class ColorWash:
    def __init__(self, ctx, color=(200, 70, 255), strength=0.12):
        self.c, self.s = np.array(color, np.float32) / 255.0, strength * min(ctx.K, 1.3)

    def render(self, fr, t, e):
        fr += (255 - fr) * self.c * (self.s * e)


@generator('camera', {
    'zoom': ('float', 0.02, 'push-in máximo (0.02 = 2%). Vale 0 nas pontas do loop'),
    'drift': ('list', [0, 0], '[dx, dy] deriva máxima em px (espaço 2048)'),
    'rotate': ('float', 0.0, 'rotação máxima da câmera (graus)'),
    'pivot': ('list', None, '[x, y] centro do movimento (opcional; padrão: centro do quadro)'),
}, 'Movimento de CÂMERA sobre tudo que está abaixo dele na pilha (push-in suave + deriva). Dá vida a qualquer capa, mesmo sem camadas móveis.')
class Camera:
    def __init__(self, ctx, zoom=0.02, drift=(0, 0), rotate=0.0, pivot=None):
        self.W, self.K, self.sc = ctx.W, ctx.K, ctx.sc
        self.zoom, self.drift, self.rot = zoom, drift, rotate
        self.pv = (pivot[0] * ctx.sc, pivot[1] * ctx.sc) if pivot else (ctx.W / 2, ctx.W / 2)

    def render(self, fr, t, e):
        s = 1 + self.zoom * self.K * e
        ang = math.radians(self.rot * self.K * math.sin(TAU * t))
        tx = self.drift[0] * self.sc * self.K * math.sin(TAU * t)
        ty = self.drift[1] * self.sc * self.K * math.sin(TAU * t)
        if abs(s - 1) + abs(ang) + abs(tx) + abs(ty) < 1e-7:
            return
        cx, cy = self.pv
        cs, sn = math.cos(ang) * s, math.sin(ang) * s
        M = np.array([[cs, -sn, cx - cs * cx + sn * cy + tx], [sn, cs, cy - sn * cx - cs * cy + ty]], np.float32)
        fr[:] = cv2.warpAffine(fr, M, (self.W, self.W), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
