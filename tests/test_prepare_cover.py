import cv2, numpy as np
import prepare_cover as pc


def synthetic_cover_with_badge(size=2048):
    img = np.full((size, size, 3), (60, 20, 70), np.uint8)
    rng = np.random.default_rng(1)
    img = np.clip(img + rng.normal(0, 6, img.shape), 0, 255).astype(np.uint8)
    x0, y0, x1, y1 = 60, size - 330, 400, size - 110
    cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 0), -1)
    cv2.rectangle(img, (x0 + 8, y0 + 8), (x1 - 8, y1 - 8), (250, 250, 250), -1)
    for i in range(3):   # "texto" preto dentro da caixa branca
        yy = y0 + 30 + i * 60
        cv2.rectangle(img, (x0 + 25, yy), (x1 - 25, yy + 35), (0, 0, 0), -1)
    return img, (x0, y0, x1, y1)


def test_detect_and_remove_badge():
    img, (x0, y0, x1, y1) = synthetic_cover_with_badge()
    box = pc.detect_badge(img)
    assert box is not None
    bx0, by0, bx1, by1 = box
    assert abs(bx0 - x0) < 40 and abs(by0 - y0) < 40 and abs(bx1 - x1) < 40 and abs(by1 - y1) < 40
    out = pc.remove_region(img, box)
    region = out[y0 + 10:y1 - 10, x0 + 10:x1 - 10]
    assert (cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) > 200).mean() < 0.02   # sem branco do selo


def test_no_badge_returns_none():
    img = np.full((2048, 2048, 3), (60, 20, 70), np.uint8)
    assert pc.detect_badge(img) is None
