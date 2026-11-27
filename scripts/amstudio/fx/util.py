import cv2, numpy as np


def noise(h, w, cell, amp, seed):
    """Ruído suave 2D (campo de deslocamento). `cell` e `amp` em pixels do canvas de trabalho."""
    r = np.random.default_rng(seed)
    cell = max(4, int(cell))
    f = r.normal(0, 1, (h // cell + 2, w // cell + 2)).astype(np.float32)
    f = cv2.resize(f, (w, h), interpolation=cv2.INTER_CUBIC)
    return cv2.GaussianBlur(f, (0, 0), cell / 3) * amp * 2.2


def odd(n):
    n = max(1, int(round(n)))
    return n if n % 2 else n + 1


def ell(k):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (odd(k), odd(k)))


def palette(cover):
    """Duas cores vivas dominantes da capa (BGR) para vazamentos de luz."""
    px = cv2.resize(cover, (64, 64)).reshape(-1, 3).astype(np.float32)
    hv = cv2.cvtColor(px.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2HSV).reshape(-1, 3)
    cand = px[(hv[:, 1] > 110) & (hv[:, 2] > 150)]
    if len(cand) < 20:
        return (170, 60, 255), (40, 110, 255)
    _, _, centers = cv2.kmeans(cand, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
    c = [tuple(float(v) * 255 / max(max(cc), 1) for v in cc) for cc in centers]
    return c[0], c[1]
