"""Separa uma capa ACHATADA em camadas (fundo limpo / título / sujeito) por IA + heurísticas.

As camadas são salvas como PNG em `assets/` (você pode abri-las e editá-las no Photoshop/GIMP!) e a cena
referencia esses arquivos. Garantia: composição das camadas no frame 0 == capa original.
Análise em 2048 px; os arquivos saem na resolução NATIVA da capa (3000, 3840, 4096…).
"""
import hashlib, os
import cv2, numpy as np
from . import REF
from .compat import imread, imwrite


def _ell(k):
    k = max(1, int(k)); k += (k % 2 == 0)
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))


def _subject_masks(cov2, cache):
    h = hashlib.sha1(cov2.tobytes()).hexdigest()[:12]
    p = os.path.join(cache, f'masks_{h}.npz')
    if not os.path.exists(p):
        try:
            from rembg import new_session, remove
        except ImportError as e:
            raise RuntimeError('Recorte de sujeito precisa de IA: pip install -r requirements-ai.txt '
                               '(ou use "subject": {"enabled": false})') from e
        from PIL import Image
        im = Image.fromarray(cv2.cvtColor(cov2, cv2.COLOR_BGR2RGB))
        u = np.array(remove(im, session=new_session('u2net'), only_mask=True), np.float32) / 255
        i = np.array(remove(im, session=new_session('isnet-general-use'), only_mask=True), np.float32) / 255
        np.savez_compressed(p, u=u, i=i)
    d = np.load(p)
    return d['u'], d['i']


def derive_subject_box(mask, margin=0.06, safe_h=1251):
    """Caixa do sujeito a partir de uma máscara (0..1, 2048²): [x0,y0,x1,y1], pivô (base-centro) e faixa vertical-chave p/ o 3:4.
    Usa percentis (0,5–99,5) para ignorar manchas isoladas. Retorna None se a máscara for pequena demais."""
    ys, xs = np.where(mask > 0.5)
    if len(xs) < 2000:
        return None
    S = mask.shape[0]
    x0, x1 = np.percentile(xs, [0.5, 99.5]); y0, y1 = np.percentile(ys, [0.5, 99.5])
    m = margin * S
    box = [int(max(0, x0 - m)), int(max(0, y0 - m)), int(min(S, x1 + m)), int(min(S, y1 + m))]
    key = [max(0, box[1] - 30), min(S, max(box[3], box[1] + 400))]
    if key[1] - key[0] > safe_h:                      # sujeito mais alto que a Safe Area: prioriza a parte de cima (rosto/tronco)
        key[1] = key[0] + safe_h
    return {'box': box, 'pivot': [int((box[0] + box[2]) / 2), box[3]], 'key_content_y': key}


def build(cov, cfg, project_dir):
    """cov: BGR uint8 nativa (quadrada). cfg: config v1 (subject/title/...). Retorna dict 'built'."""
    N, S = cov.shape[0], REF
    cache = os.path.join(project_dir, '.cache'); os.makedirs(cache, exist_ok=True)
    assets = os.path.join(project_dir, 'assets'); os.makedirs(assets, exist_ok=True)
    cov2 = cv2.resize(cov, (S, S), interpolation=cv2.INTER_AREA) if N != S else cov
    up = (lambda x: cv2.resize(x, (N, N), interpolation=cv2.INTER_CUBIC)) if N != S else (lambda x: x)

    sub = cfg.get('subject') or {}
    sub_on = sub.get('enabled', True) and cfg.get('subject') is not None
    auto = None
    if sub_on:
        u_m, i_m = _subject_masks(cov2, cache)
        sel = np.zeros((S, S), np.float32)
        boxes = list(sub.get('isnet_boxes', []))
        if sub.get('auto') or not boxes:              # caixa derivada da máscara (sem coordenadas à mão)
            auto = derive_subject_box(u_m)
            if auto:
                bx = auto['box']; pad = int(0.04 * S)
                boxes = [[max(0, bx[0] - pad), max(0, bx[1] - pad), min(S, bx[2] + pad), min(S, bx[3] + pad)]]
        for (x0, y0, x1, y1) in boxes: sel[y0:y1, x0:x1] = 1
        Mg = cv2.GaussianBlur(np.clip((np.maximum(u_m, i_m * sel) - 0.2) / 0.5, 0, 1), (0, 0), 2)
    else:
        Mg = np.zeros((S, S), np.float32)
    alpha_g = cv2.GaussianBlur(cv2.dilate(Mg, _ell(19)), (0, 0), 6)

    TT, mt = cfg.get('title'), np.zeros((S, S), np.float32)
    if TT:
        hsv = cv2.cvtColor(cov2, cv2.COLOR_BGR2HSV).astype(np.float32)
        V, Sat = hsv[..., 2], hsv[..., 1] / 255
        col = ((V > 95) | ((Sat > 0.5) & (V > 60))).astype(np.uint8)
        gray = cv2.cvtColor(cov2, cv2.COLOR_BGR2GRAY).astype(np.float32)
        gm = np.hypot(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
        texm = cv2.dilate((cv2.GaussianBlur(gm, (0, 0), 14) > TT.get('texture_thr', 55)).astype(np.uint8), _ell(41))
        tx0, ty0, tx1, ty1 = TT['box']
        box = np.zeros((S, S), np.uint8); box[ty0:ty1, tx0:tx1] = 1
        m = col * box * texm * (cv2.dilate(Mg, _ell(41)) < 0.2).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, _ell(31))
        mt = cv2.morphologyEx(m, cv2.MORPH_OPEN, _ell(5)).astype(np.float32)
    alpha_t = cv2.GaussianBlur(cv2.dilate(mt, _ell(15)), (0, 0), 4)

    Mi = np.maximum(alpha_g > 0.97, alpha_t > 0.97).astype(np.float32)
    sm = cv2.resize(cov2, (512, 512), interpolation=cv2.INTER_AREA)
    mk = (cv2.resize(cv2.dilate(Mi, _ell(5)), (512, 512)) > 0.3).astype(np.uint8) * 255
    inp = cv2.inpaint(sm, mk, 9, cv2.INPAINT_TELEA)
    inp = cv2.GaussianBlur(cv2.resize(inp, (S, S), interpolation=cv2.INTER_CUBIC), (0, 0), 4)
    Mis = up(cv2.GaussianBlur(Mi, (0, 0), 2))[..., None]
    bg = (cov.astype(np.float32) * (1 - Mis) + up(inp).astype(np.float32) * Mis).astype(np.uint8)
    imwrite(os.path.join(assets, 'bg.png'), bg)
    built = {'bg': {'asset': 'assets/bg.png', 'bbox': [0, 0, S, S]}, 'title': None, 'subject': None}

    k = N / S
    def crop_png(name, alpha2, x0, y0, x1, y1):
        a = np.clip(up(alpha2), 0, 1)
        X0, Y0, X1, Y1 = int(round(x0 * k)), int(round(y0 * k)), int(round(x1 * k)), int(round(y1 * k))
        bgra = np.dstack([cov, (a * 255).astype(np.uint8)])[Y0:Y1, X0:X1]
        imwrite(os.path.join(assets, f'{name}.png'), bgra)
        return {'asset': f'assets/{name}.png', 'bbox': [x0, y0, x1, y1]}

    if TT and mt.sum() > 0:
        built['title'] = crop_png('title', alpha_t, *TT['box'])
    if sub_on and Mg.sum() > 0:
        if auto:
            bx = auto['box']; pad = int(0.05 * S)
            bx = [max(0, bx[0] - pad), max(0, bx[1] - pad), min(S, bx[2] + pad), min(S, bx[3] + pad)]
            built['subject'] = crop_png('subject', alpha_g, *bx)
            built['subject']['pivot'] = auto['pivot']
            built['key_content_y'] = auto['key_content_y']
        else:
            ox, oy = sub.get('bbox_origin', [640, 150])
            built['subject'] = crop_png('subject', alpha_g, ox, oy, S, S)
    return built
