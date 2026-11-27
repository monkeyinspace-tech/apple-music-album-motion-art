"""Entrada de arquivos: PNG/JPG/TIFF/PSD, qualquer tamanho quadrado (2048, 3000, 3840, 4096…), sRGB, selo explícito."""
import io, os
import cv2, numpy as np
from PIL import Image, ImageCms

Image.MAX_IMAGE_PIXELS = None


def load_srgb(path):
    """Retorna (BGR uint8, nota). Converte perfil ICC para sRGB; PSD → composição achatada."""
    if path.lower().endswith(('.psd', '.psb')):
        from psd_tools import PSDImage
        pil = PSDImage.open(path).composite()
        return cv2.cvtColor(np.array(pil.convert('RGB')), cv2.COLOR_RGB2BGR), 'PSD achatado (composição)'
    im = Image.open(path)
    icc = im.info.get('icc_profile')
    if im.mode in ('I;16', 'I'):
        im = Image.fromarray((np.array(im) / 257).astype(np.uint8))
    im = im.convert('RGB')
    note = 'sem perfil ICC (assumido sRGB)'
    if icc:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            name = ImageCms.getProfileDescription(src).strip()
            if 'sRGB' not in name:
                im = ImageCms.profileToProfile(im, src, ImageCms.createProfile('sRGB'), outputMode='RGB')
                note = f'convertido de "{name}" para sRGB'
            else:
                note = f'perfil já é {name}'
        except Exception as e:
            note = f'perfil ICC ilegível ({e}); assumido sRGB'
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR), note


def describe_size(w, h):
    """Classifica o tamanho para orientar o usuário."""
    side = min(w, h)
    cls = ('menor que 2048 px (será AMPLIADA)' if side < 2048 else '2048 px' if side < 2500 else
           '3000 px (padrão de capas de lançamento)' if side < 3500 else '4K (3840 px)' if side < 4000 else f'{side} px (acima de 4K)')
    return {'w': w, 'h': h, 'square': w == h, 'class': cls}


def fit_square(img, mode='error'):
    """Torna a imagem quadrada. mode: error | crop (recorte central) | extend (estende com borda desfocada)."""
    h, w = img.shape[:2]
    if h == w: return img
    if mode == 'error':
        raise ValueError(f'A imagem não é quadrada ({w}x{h}). Use --fit crop (recorta ao centro) ou --fit extend (estende as bordas).')
    if mode == 'crop':
        s = min(w, h); x0, y0 = (w - s) // 2, (h - s) // 2
        return img[y0:y0 + s, x0:x0 + s]
    s = max(w, h)
    bg = cv2.GaussianBlur(cv2.resize(img, (s, s), interpolation=cv2.INTER_AREA), (0, 0), s / 40)
    bg = (bg.astype(np.float32) * 0.6).astype(np.uint8)
    x0, y0 = (s - w) // 2, (s - h) // 2
    bg[y0:y0 + h, x0:x0 + w] = img
    return bg


def working_size(src_side, requested='auto'):
    """Tamanho de trabalho do 1:1. auto = nativo até 3840 (mínimo 2048)."""
    if requested != 'auto': return int(requested)
    return int(max(2048, min(src_side, 3840)))


# ---- selo Parental Advisory --------------------------------------------------------------
def detect_badge(img):
    h, w = img.shape[:2]
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    white = (g > 215).astype(np.uint8)
    k = max(3, int(25 * w / 2048))
    white = cv2.morphologyEx(white, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    n, _, stats, _ = cv2.connectedComponentsWithStats(white)
    best = None
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if area < 0.004 * w * h or area > 0.08 * w * h: continue
        if not (1.3 <= bw / max(bh, 1) <= 2.4): continue
        cx, cy = x + bw / 2, y + bh / 2
        if not ((cx < 0.3 * w or cx > 0.7 * w) and (cy < 0.25 * h or cy > 0.7 * h)): continue
        roi = g[y:y + bh, x:x + bw]
        dark, fill = (roi < 60).mean(), (roi > 215).mean()
        if 0.25 < dark < 0.75 and 0.2 < fill < 0.7 and (best is None or area > best[0]):
            best = (area, (int(x), int(y), int(x + bw), int(y + bh)))
    return best[1] if best else None


def remove_region(img, box, margin=14):
    h, w = img.shape[:2]
    mg = int(margin * w / 2048)
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = max(x0 - mg, 0), max(y0 - mg, 0), min(x1 + mg, w), min(y1 + mg, h)
    m = np.zeros((h, w), np.uint8); m[y0:y1, x0:x1] = 255

    def fill(size, rad):
        sm = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
        ms = (cv2.resize(m, (size, size), interpolation=cv2.INTER_AREA) > 20).astype(np.uint8) * 255
        return cv2.resize(cv2.inpaint(sm, ms, rad, cv2.INPAINT_NS), (w, h), interpolation=cv2.INTER_CUBIC)

    coarse, fine = fill(256, 9), fill(1024, 13)
    inp = cv2.GaussianBlur(0.5 * coarse.astype(np.float32) + 0.5 * fine.astype(np.float32), (0, 0), 5 * w / 2048)
    bh = y1 - y0
    sy = y0 - bh if y0 - bh >= 0 else min(y1, h - bh)
    src = img[sy:sy + bh, x0:x1].astype(np.float32)
    hf = src - cv2.GaussianBlur(src, (0, 0), 6 * w / 2048)
    tex = np.zeros_like(inp); tex[y0:y1, x0:x1] = hf * 0.7
    a = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 9 * w / 2048)[..., None]
    return np.clip(img.astype(np.float32) * (1 - a) + np.clip(inp + tex, 0, 255) * a, 0, 255).astype(np.uint8)
