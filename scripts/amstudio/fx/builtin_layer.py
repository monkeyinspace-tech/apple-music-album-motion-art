"""Efeitos de CAMADA embutidos. Operam sobre os pixels (BGR pré-multiplicado + alfa) de uma camada de imagem."""
import math
import cv2, numpy as np
from . import layer_fx
from .util import noise, ell, odd
from ..curves import evaluate

TAU = 2 * math.pi


@layer_fx('flow', {
    'amp': ('float', 13.0, 'deslocamento máximo em px (espaço 2048). Fumaça viva / ondulação orgânica'),
    'amp2': ('float', None, 'amplitude do 2º campo (padrão 0.85×amp)'),
    'cell': ('float', 220, 'escala do 1º campo (px). Maior = movimentos mais largos'),
    'cell2': ('float', 300, 'escala do 2º campo'),
    'seed': ('int', 1, 'semente'),
    'protect': ('list', None, 'elipses que NÃO deformam: [{"center":[x,y],"axes":[a,b]}]'),
    'protect_layers': ('list', None, 'ids de camadas cujo contorno também fica protegido (ex.: ["subject"])'),
}, 'Deforma suavemente a camada com campos de ruído periódicos (fumaça, água, tecido). Zero em t=0 e t=1.')
class Flow:
    def __init__(self, ctx, layer, amp=13.0, amp2=None, cell=220, cell2=300, seed=1, protect=None, protect_layers=None):
        sc, h, w = ctx.sc, layer.h, layer.w
        a1, a2 = amp * sc * ctx.K, (amp2 if amp2 is not None else amp * 0.85) * sc * ctx.K
        self.sc, self.layer, self.protect_layers = sc, layer, protect_layers or []
        self.FA = [noise(h, w, cell * sc, a1, seed), noise(h, w, cell * sc, a1, seed + 1)]
        self.FB = [noise(h, w, cell2 * sc, a2, seed + 2), noise(h, w, cell2 * sc, a2, seed + 3)]
        ew = np.ones((h, w), np.float32)
        for pr in protect or []:
            cx, cy = pr['center']; ax, ay = pr['axes']
            cv2.ellipse(ew, (int(cx * sc - layer.x0), int(cy * sc - layer.y0)), (int(ax * sc), int(ay * sc)), 0, 0, 360, 0, -1)
        self.ew = cv2.GaussianBlur(ew, (0, 0), 60 * sc) if protect else ew
        self.gx, self.gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        self._linked = False

    def link(self, ctx, layers):
        for lid in self.protect_layers:
            al = layers[lid].canvas_alpha()[self.layer.y0:self.layer.y0 + self.layer.h, self.layer.x0:self.layer.x0 + self.layer.w]
            self.ew = self.ew * np.clip(1 - cv2.GaussianBlur(al, (0, 0), 25 * self.sc) * 2, 0, 1)
        for L in (self.FA, self.FB):
            for i in range(2): L[i] = L[i] * self.ew

    def apply(self, img, t, e):
        s1 = math.sin(TAU * t)
        return cv2.remap(img, self.gx + self.FA[0] * s1 + self.FB[0] * e, self.gy + self.FA[1] * s1 + self.FB[1] * e,
                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


@layer_fx('boil', {
    'amp': ('float', 1.6, 'tremor em px (espaço 2048). Limitado a max_amp por acessibilidade'),
    'max_amp': ('float', 2.4, 'teto do tremor (px)'),
    'cell': ('float', 70, 'tamanho das "peças" que tremem independentes (px)'),
    'rate': ('float', 6.0, 'trocas por segundo (estilo stop-motion/zine)'),
    'seed': ('int', 100, 'semente'),
}, 'Tremor estilo "boil"/zine: cada peça de papel/letra balança de leve, em passos discretos. O passo 0 é neutro.')
class Boil:
    def __init__(self, ctx, layer, amp=1.6, max_amp=2.4, cell=70, rate=6.0, seed=100):
        self.ctx, self.layer, self.cell, self.rate, self.seed = ctx, layer, cell, rate, seed
        self.a = min(amp * ctx.K, max_amp) * ctx.sc
        self.gx, self.gy = np.meshgrid(np.arange(layer.w, dtype=np.float32), np.arange(layer.h, dtype=np.float32))
        self._k, self._maps = -1, None

    def apply(self, img, t, e):
        k = int(t * self.rate * self.ctx.dur)
        if k == 0:
            return img
        if k != self._k:
            h, w, c = self.layer.h, self.layer.w, self.cell * self.ctx.sc
            self._maps = (self.gx + noise(h, w, c, self.a, self.seed + k), self.gy + noise(h, w, c, self.a, self.seed + 200 + k))
            self._k = k
        return cv2.remap(img, self._maps[0], self._maps[1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


@layer_fx('shine', {
    'width': ('float', 170, 'largura da faixa de brilho (px)'),
    'strength': ('float', 0.40, 'intensidade (0..1)'),
    'slope': ('float', 0.6, 'inclinação da faixa'),
    'color': ('color', [255, 235, 255], 'cor BGR do brilho'),
    'start': ('float', -700, 'posição inicial da faixa (fora da peça)'),
    'inset': ('float', 15, 'recuo (px) para brilhar só no miolo opaco da camada'),
}, 'Faixa de luz diagonal que varre a camada uma vez por loop (como brilho em letreiro/metal).')
class Shine:
    def __init__(self, ctx, layer, width=170, strength=0.40, slope=0.6, color=(255, 235, 255), start=-700, inset=15):
        sc = ctx.sc
        a = (layer.base[..., 3] > 0.5).astype(np.uint8)
        a = cv2.erode(a, ell(2 * inset * sc + 1))
        self.core = cv2.GaussianBlur(a.astype(np.float32), (0, 0), 3 * sc)
        xr = (np.arange(layer.w, dtype=np.float32) + layer.x0) / sc
        yr = (np.arange(layer.h, dtype=np.float32) + layer.y0) / sc
        self.U = xr[None, :] + slope * yr[:, None]
        self.width, self.start, self.color = width, start, np.array(color, np.float32)
        self.travel = layer.ref_w + slope * layer.ref_h + 1500
        self.s = strength * min(ctx.K, 1.3)

    def apply(self, img, t, e):
        band = np.exp(-((self.U - (self.start + t * self.travel)) / self.width) ** 2)
        if band.max() < 1e-3:
            return img
        img = img.copy()
        img[..., :3] += (band * self.core * self.s)[..., None] * self.color
        return img


@layer_fx('wave', {
    'amp': ('float', 6.0, 'amplitude (px)'), 'wavelength': ('float', 300, 'comprimento de onda (px)'),
    'cycles': ('int', 1, 'ondas que "passam" por loop'), 'axis': ('str', 'x', '"x" desloca colunas de pixels ao longo de y; "y" o inverso'),
}, 'Ondulação senoidal (bandeira, água, calor). Zero em t=0 e t=1.')
class Wave:
    def __init__(self, ctx, layer, amp=6.0, wavelength=300, cycles=1, axis='x'):
        self.a, self.lam, self.n, self.axis = amp * ctx.sc * ctx.K, wavelength * ctx.sc, cycles, axis
        self.gx, self.gy = np.meshgrid(np.arange(layer.w, dtype=np.float32), np.arange(layer.h, dtype=np.float32))

    def apply(self, img, t, e):
        c = self.gy if self.axis == 'x' else self.gx
        d = self.a * (np.sin(TAU * (c / self.lam + self.n * t)) - np.sin(TAU * c / self.lam))
        mx, my = (self.gx + d, self.gy) if self.axis == 'x' else (self.gx, self.gy + d)
        return cv2.remap(img, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


@layer_fx('blur', {'radius': ('spec', {'env': True, 'amp': 8}, 'raio do desfoque (px, animável)')},
          'Desfoque gaussiano animável (foco/desfoco, "respiração" de lente).')
class Blur:
    def __init__(self, ctx, layer, radius=None):
        self.ctx, self.radius = ctx, radius if radius is not None else {'env': True, 'amp': 8}

    def apply(self, img, t, e):
        r = evaluate(self.radius, t) * self.ctx.sc * self.ctx.K
        return img if r < 0.3 else cv2.GaussianBlur(img, (0, 0), r)


@layer_fx('glow', {
    'radius': ('float', 30, 'raio do bloom (px)'), 'threshold': ('float', 0.65, 'luminância mínima (0..1) que brilha'),
    'strength': ('spec', {'env': True, 'amp': 0.6}, 'intensidade animável'),
}, 'Bloom: as áreas claras da camada irradiam luz. Intensidade animável (pulsar).')
class Glow:
    def __init__(self, ctx, layer, radius=30, threshold=0.65, strength=None):
        self.ctx, self.r, self.th = ctx, radius * ctx.sc, threshold
        self.strength = strength if strength is not None else {'env': True, 'amp': 0.6}

    def apply(self, img, t, e):
        s = evaluate(self.strength, t) * min(self.ctx.K, 1.3)
        if s < 1e-3: return img
        a = np.maximum(img[..., 3:4], 1e-3)
        lum = (img[..., :3] / a).mean(axis=2, keepdims=True) / 255.0
        m = np.clip((lum - self.th) / (1 - self.th), 0, 1) * img[..., 3:4]
        bl = cv2.GaussianBlur(img[..., :3] * m, (0, 0), self.r)
        out = img.copy(); out[..., :3] += bl * s
        return out


@layer_fx('tint', {
    'hue': ('spec', 0, 'rotação de matiz (graus, animável)'), 'sat': ('spec', 0, 'delta de saturação (-1..1)'),
    'bright': ('spec', 0, 'delta de brilho (-1..1)'),
}, 'Correção de cor animável: gire o matiz, pulse a saturação ou o brilho (respire a cor).')
class Tint:
    def __init__(self, ctx, layer, hue=0, sat=0, bright=0):
        self.hue, self.sat, self.bright, self.K = hue, sat, bright, ctx.K

    def apply(self, img, t, e):
        h, s, b = evaluate(self.hue, t) * self.K, evaluate(self.sat, t) * self.K, evaluate(self.bright, t) * self.K
        if abs(h) < 1e-3 and abs(s) < 1e-4 and abs(b) < 1e-4: return img
        a = np.maximum(img[..., 3:4], 1e-3)
        c = np.clip(img[..., :3] / a / 255.0, 0, 1).astype(np.float32)
        hsv = cv2.cvtColor(c, cv2.COLOR_BGR2HSV)
        hsv[..., 0] = (hsv[..., 0] + h) % 360
        hsv[..., 1] = np.clip(hsv[..., 1] * (1 + s), 0, 1)
        hsv[..., 2] = np.clip(hsv[..., 2] * (1 + b), 0, 1)
        out = img.copy()
        out[..., :3] = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR) * 255.0 * img[..., 3:4]
        return out


@layer_fx('chroma', {'shift': ('spec', {'env': True, 'amp': 4}, 'separação dos canais R/B (px, animável)')},
          'Aberração cromática: separa levemente os canais de cor (efeito de lente/VHS), sem piscar.')
class Chroma:
    def __init__(self, ctx, layer, shift=None):
        self.ctx, self.shift = ctx, shift if shift is not None else {'env': True, 'amp': 4}

    def apply(self, img, t, e):
        d = evaluate(self.shift, t) * self.ctx.sc * self.ctx.K
        if abs(d) < 0.2: return img
        out = img.copy(); h, w = img.shape[:2]
        for ch, sgn in ((0, 1), (2, -1)):
            M = np.float32([[1, 0, sgn * d], [0, 1, 0]])
            out[..., ch] = cv2.warpAffine(img[..., ch], M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return out
