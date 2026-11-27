#!/usr/bin/env python3
"""Gera as ilustrações da documentação (docs/assets/*.png) a partir da arte de DEMONSTRAÇÃO (CC0).

Tudo é desenhado do zero (Pillow) — NÃO usa imagens, telas ou ícones da Apple nem capas de terceiros.
Os mockups são genéricos (barras de esqueleto no lugar de texto) e só imitam a *ideia* de layout da página de álbum.
Uso: python tools/make_docs_images.py [--out docs/assets]
"""
import argparse, math, os, subprocess, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from amstudio import scene as S, outputs
from amstudio.engine import Renderer

FB = next((p for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf') if os.path.exists(p)), None)
FR = next((p for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'C:/Windows/Fonts/arial.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf') if os.path.exists(p)), None)
PINK = (255, 79, 163)
SK = (90, 80, 105)


def font(sz, bold=False):
    p = FB if bold else FR
    return ImageFont.truetype(p, sz) if p else ImageFont.load_default()


def to_pil(bgr): return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def gradient(w, h, c1, c2):
    a = np.linspace(0, 1, h)[:, None, None]
    return Image.fromarray(((np.array(c1)[None, None, :] * (1 - a) + np.array(c2)[None, None, :] * a) * np.ones((h, w, 1))).astype(np.uint8))


def shadow(img, box, blur=24, alpha=140, off=(0, 14)):
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([box[0] + off[0], box[1] + off[1], box[2] + off[0], box[3] + off[1]], 30, fill=(0, 0, 0, alpha))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


def sk(d, x, y, w, h=10, col=SK):
    d.rounded_rectangle([x, y, x + w, y + h], 5, fill=col)


def demo_project(tmp):
    proj = os.path.join(tmp, 'demo')
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'studio.py'), 'init', os.path.join(ROOT, 'examples', 'demo', 'demo_cover.png'), proj,
                    '--template', os.path.join(ROOT, 'examples', 'demo', 'demo_config.json')], check=True, capture_output=True)
    return proj


def frames(proj, W=900, ts=(0, .2, .4, .5, .7, .9)):
    sc = S.load(proj); r = Renderer(proj, sc, W)
    ext = outputs.Ext3x4(r.ctx.cover, sc['output']['key_content_y'], W)
    sq, tall = [], []
    for t in ts:
        f = r.frame(int(round(t * r.N))); sq.append(to_pil(f)); tall.append(to_pil(ext.make(f)))
    return sq, tall


def head(img, title, sub=None, sub2=None):
    d = ImageDraw.Draw(img)
    d.text((60, 34), title, font=font(40, True), fill=(255, 255, 255))
    if sub: d.text((60, 90), sub, font=font(21), fill=(210, 190, 225))
    if sub2: d.text((60, 126), sub2, font=font(21, True), fill=(255, 190, 220))
    return d


def where_it_appears(out, sq, tall):
    W, H = 1700, 940
    img = gradient(W, H, (28, 14, 48), (9, 6, 16)).convert('RGBA')
    d = head(img, 'Onde o Album Motion aparece', 'Na página do álbum (iPhone, iPad, Mac e Apple TV) e, às vezes, em "Ouvir Agora" — no lugar da capa estática.',
             'Loop contínuo de 8 a 35 s, sem áudio. O 1º quadro é a capa estática; a animação parte dela.')
    pad = [520, 190, 1640, 890]; shadow(img, pad)
    d.rounded_rectangle(pad, 46, fill=(24, 20, 34), outline=(70, 60, 90), width=4)
    scr = [pad[0] + 22, pad[1] + 22, pad[2] - 22, pad[3] - 22]
    d.rounded_rectangle(scr, 30, fill=(34, 30, 46)); d.rounded_rectangle([scr[0], scr[1], scr[0] + 210, scr[3]], 30, fill=(28, 24, 40))
    for i, w in enumerate((120, 90, 110, 80, 100, 70, 105)): sk(d, scr[0] + 26, scr[1] + 40 + i * 44, w, 12)
    cx, cy, cs = scr[0] + 250, scr[1] + 58, 330
    art = sq[3].resize((cs, cs), Image.LANCZOS).convert('RGBA')
    m = Image.new('L', (cs, cs), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, cs, cs], 18, fill=255)
    shadow(img, [cx, cy, cx + cs, cy + cs], 14, 160, (0, 8)); img.paste(art, (cx, cy), m)
    d = ImageDraw.Draw(img); d.rounded_rectangle([cx - 4, cy - 4, cx + cs + 4, cy + cs + 4], 22, outline=PINK, width=4)
    tx = cx + cs + 40
    sk(d, tx, cy + 14, 300, 22, (235, 225, 245)); sk(d, tx, cy + 54, 190, 16, (255, 140, 190)); sk(d, tx, cy + 86, 120, 10)
    for i in range(3): sk(d, tx, cy + 130 + i * 20, 400 - i * 60, 9)
    for x0 in (tx, tx + 150): d.rounded_rectangle([x0, cy + 220, x0 + 130, cy + 262], 14, fill=(74, 58, 100))
    d.text((tx + 30, cy + 229), '▶  Play', font=font(18, True), fill=(255, 190, 220)); d.text((tx + 180, cy + 229), 'Shuffle', font=font(18, True), fill=(255, 190, 220))
    for i in range(7):
        y = cy + cs + 38 + i * 38
        if y > scr[3] - 30: break
        sk(d, cx, y, 40 + (i * 53) % 150, 11); sk(d, scr[2] - 120, y, 46, 9); d.line([cx, y + 24, scr[2] - 40, y + 24], fill=(55, 50, 72), width=1)
    d.text((cx + 6, cy - 34), '1:1 · 3840×3840', font=font(18, True), fill=PINK)
    ph = [110, 210, 440, 900]; shadow(img, ph, 28, 170)
    d.rounded_rectangle(ph, 56, fill=(20, 16, 28), outline=(80, 70, 100), width=5)
    s = [ph[0] + 12, ph[1] + 12, ph[2] - 12, ph[3] - 12]; d.rounded_rectangle(s, 46, fill=(34, 30, 46))
    sw, sh = s[2] - s[0], s[3] - s[1]
    art = tall[3].resize((sw, int(sw * 2732 / 2048)), Image.LANCZOS); art = art.crop((0, 0, sw, min(art.height, int(sh * 0.62))))
    mk = Image.new('L', art.size, 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, art.width, art.height + 60], 46, fill=255)
    img.paste(art.convert('RGBA'), (s[0], s[1]), mk)
    g = Image.new('RGBA', (sw, 150), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    for i in range(150): gd.line([0, i, sw, i], fill=(34, 30, 46, int(255 * (i / 150) ** 1.4)))
    img.alpha_composite(g, (s[0], s[1] + art.height - 150)); d = ImageDraw.Draw(img); y = s[1] + art.height + 8
    sk(d, s[0] + 24, y, 170, 16, (235, 225, 245)); sk(d, s[0] + 24, y + 28, 110, 11, (255, 140, 190))
    for x0 in (s[0] + 24, s[0] + 152): d.rounded_rectangle([x0, y + 58, x0 + 116, y + 94], 12, fill=(74, 58, 100))
    for i in range(3): sk(d, s[0] + 24, y + 118 + i * 30, 180 - i * 30, 9)
    d.text((ph[0] + 6, ph[1] - 36), '3:4 · 2048×2732', font=font(18, True), fill=PINK)
    d.polygon([(510, 360), (498, 354), (498, 366)], fill=PINK); d.line([445, 360, 498, 360], fill=PINK, width=3)
    d.text((60, 906), 'Ilustração original, com arte de demonstração. Não usa imagens da Apple. Apple Music é marca da Apple Inc.', font=font(15), fill=(150, 135, 170))
    img.convert('RGB').save(os.path.join(out, 'where-it-appears.png'))


def safe_area(out, tall):
    W, H = 1500, 1000
    img = gradient(W, H, (24, 12, 40), (9, 6, 16)).convert('RGBA')
    d = head(img, 'As áreas do formato 3:4 (2048 × 2732 px)')
    fh = 800; fw = int(fh * 2048 / 2732); fx, fy = 70, 130; k = fh / 2732.0
    img.paste(tall[3].resize((fw, fh), Image.LANCZOS).convert('RGBA'), (fx, fy))
    sa = [fx + 49 * fw / 2048, fy + 458 * k, fx + 2003 * fw / 2048, fy + 1709 * k]
    ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rectangle([fx, fy, fx + fw, sa[1]], fill=(30, 30, 40, 150)); od.rectangle([fx, sa[3], fx + fw, fy + fh], fill=(30, 30, 40, 170))
    img.alpha_composite(ov); d = ImageDraw.Draw(img)
    d.rectangle(sa, outline=(60, 230, 120), width=4); d.rectangle([fx, fy, fx + fw, fy + fh], outline=PINK, width=4)
    for i in range(2): sk(d, fx + 30, fy + 25 + i * 26, int(fw * (0.5 - 0.1 * i)), 10, (190, 180, 205))
    for i in range(3): sk(d, int(fx + 30), int(sa[3] + 24 + i * 26), int(fw * (0.55 - 0.1 * i)), 10, (190, 180, 205))
    d.text((fx + 12, sa[1] + 6), 'ART SAFE AREA', font=font(16, True), fill=(60, 230, 120)); d.text((fx + 12, fy + 6), 'ARTWORK AREA', font=font(16, True), fill=PINK)
    tx = 520
    for i, (c, a, b) in enumerate([((60, 230, 120), 'Art Safe Area  ≈ x 49–2003 · y 458–1709', 'Texto, logos e elementos-chave ficam aqui — o app não cobre a arte.'),
                                   (PINK, 'Artwork Area  (canvas inteiro)', 'A arte vai de ponta a ponta — sem bordas nem molduras.'),
                                   ((190, 180, 205), 'Zona de UI (topo e base)', 'Botões, título e gradiente escuro do app podem cobrir a arte.')]):
        yy = 150 + i * 150
        d.rounded_rectangle([tx, yy + 4, tx + 28, yy + 32], 6, outline=c, width=4)
        d.text((tx + 50, yy), a, font=font(26, True), fill=(255, 255, 255)); d.text((tx + 50, yy + 38), b, font=font(20), fill=(210, 190, 225))
    d.text((tx, 640), 'Neste projeto', font=font(28, True), fill=(255, 255, 255))
    for i, t in enumerate(['A capa quadrada entra em LARGURA TOTAL e é posicionada para que a faixa-chave (key_content_y)',
                           'caiba na Safe Area. Só o topo e a base são estendidos, com a textura da própria borda.',
                           'As laterais nunca são estendidas. No 1:1 (3840²) a tela inteira é Área Segura.']):
        d.text((tx, 690 + i * 34), t, font=font(20), fill=(210, 190, 225))
    d.text((60, 960), 'Medidas do template oficial "Album Page Motion Toolkit". Ilustração original com arte de demonstração.', font=font(15), fill=(150, 135, 170))
    img.convert('RGB').save(os.path.join(out, 'safe-area.png'))


def layers_explainer(out, tmp):
    psd, proj = os.path.join(tmp, 'l.psd'), os.path.join(tmp, 'psdproj')
    subprocess.run([sys.executable, os.path.join(ROOT, 'examples', 'demo', 'make_demo_psd.py'), psd, '1200'], check=True, capture_output=True)
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'studio.py'), 'init', psd, proj, '--impact', '[900,1300]'], check=True, capture_output=True)
    sc = S.load(proj)
    items = [(L.get('name') or L['id'], L.get('role'), Image.open(os.path.join(proj, L['asset'])).convert('RGBA'), L['bbox'])
             for L in sc['layers'] if L['type'] == 'image']
    nice = {'bg': 'fumaça viva + zoom suave', 'other': 'parada (ou flutuação)', 'title': 'brilho varrendo as letras', 'lock': 'travada: não se move'}
    W, H = 1700, 1000
    img = gradient(W, H, (28, 14, 48), (9, 6, 16)).convert('RGBA')
    d = head(img, 'Cada camada se move do seu jeito', 'O PSD vira uma pilha de camadas. O motor anima cada uma e recompõe tudo, quadro a quadro.')
    side = 400
    for i, (name, role, a, bb) in enumerate(items[:4]):
        layer = Image.new('RGBA', (side, side), (0, 0, 0, 0)); k = side / 2048.0
        if role == 'bg': layer.paste(a.resize((side, side), Image.LANCZOS), (0, 0))
        else:
            s = a.resize((max(8, int((bb[2] - bb[0]) * k)), max(8, int((bb[3] - bb[1]) * k))), Image.LANCZOS); layer.paste(s, (int(bb[0] * k), int(bb[1] * k)), s)
        sk_ = layer.transform((side + 200, side), Image.AFFINE, (1, 0.5, 0, 0, 1, 0), Image.BICUBIC)
        ox = 70 + i * 410; oy = 230 - 0
        shadow(img, [ox, oy + 40, ox + side * 0.8, oy + side * 0.5], 18, 120, (10, 20))
        img.alpha_composite(sk_.resize((int(sk_.width * 0.7), int(sk_.height * 0.7)), Image.LANCZOS), (ox - 10, oy + 40)); d = ImageDraw.Draw(img)
        d.text((ox, 600), f'{i + 1}. {name}', font=font(24, True), fill=(255, 255, 255)); d.text((ox, 636), nice.get(role, role or ''), font=font(18), fill=(255, 170, 210))
    d.rounded_rectangle([60, 720, W - 60, 930], 22, outline=(90, 70, 120), width=2, fill=(24, 18, 38))
    d.text((90, 744), 'Por cima das camadas entram os geradores', font=font(26, True), fill=(255, 255, 255))
    d.text((90, 788), 'vazamentos de luz · ondas de choque · estilhaços · brasas · sparkles · varredura de luz · câmera · vinheta · grão', font=font(20), fill=(255, 190, 220))
    d.text((90, 826), 'Uma camada de ajuste ("grade") reconcilia a cor com a prévia do Photoshop, para o frame 0 continuar igual à capa.', font=font(19), fill=(210, 190, 225))
    d.text((60, 962), 'Gerado de um PSD de demonstração (examples/demo/make_demo_psd.py). Arte CC0.', font=font(15), fill=(150, 135, 170))
    img.convert('RGB').save(os.path.join(out, 'layers-explainer.png'))


def loop_timeline(out, tall):
    W, H = 1700, 790
    img = gradient(W, H, (28, 14, 48), (9, 6, 16)).convert('RGBA'); d = head(img, 'O loop perfeito: tudo nasce e morre em zero')
    labels = ['t = 0\n(= capa)', 't = 0,2', 't = 0,4', 't = 0,5\n(pico)', 't = 0,7', 't = 0,9']; tw = 230; th = int(tw * 2732 / 2048)
    for i, f in enumerate(tall):
        x = 60 + i * 268; shadow(img, [x, 100, x + tw, 100 + th], 12, 130, (0, 8)); img.paste(f.resize((tw, th), Image.LANCZOS), (x, 100)); d = ImageDraw.Draw(img)
        d.rounded_rectangle([x, 100, x + tw, 100 + th], 8, outline=PINK if i in (0, 3) else (90, 70, 120), width=3 if i in (0, 3) else 1)
        d.multiline_text((x + 4, 100 + th + 8), labels[i], font=font(16, True), fill=(255, 255, 255), spacing=2)
    gx, gy, gw, gh = 60, 640, 1580, 80
    d.text((gx, 584), 'e(t) = (1 − cos 2πt) / 2   →  multiplica cada efeito', font=font(20, True), fill=(255, 190, 220))
    d.line([(gx + gw * t / 200.0, gy + gh * (1 - (1 - math.cos(2 * math.pi * t / 200.0)) / 2)) for t in range(201)], fill=PINK, width=4)
    d.line([gx, gy + gh, gx + gw, gy + gh], fill=(90, 70, 120), width=1)
    for t in (0, 1): d.ellipse([gx + gw * t - 7, gy + gh - 7, gx + gw * t + 7, gy + gh + 7], fill=(60, 230, 120))
    d.text((gx + 12, gy + gh + 8), 'começa em 0: frame 0 = capa', font=font(16), fill=(60, 230, 120)); d.text((gx + gw - 330, gy + gh + 8), 'termina em 0: fecha o loop sem salto', font=font(16), fill=(60, 230, 120))
    d.text((60, 758), 'Quadros do formato 3:4 gerados do projeto de demonstração. Arte CC0.', font=font(15), fill=(150, 135, 170))
    img.convert('RGB').save(os.path.join(out, 'loop-timeline.png'))


def social(out, tall):
    W, H = 1280, 640
    img = gradient(W, H, (40, 14, 64), (9, 6, 16)).convert('RGBA')
    gl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([780, -120, 1380, 480], fill=(255, 79, 163, 90)); img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(80)))
    for i, f in enumerate((tall[1], tall[3], tall[5])):
        w = 230; h = int(w * 2732 / 2048); x, y = 770 + i * 150, 60 + i * 30
        im = f.resize((w, h), Image.LANCZOS); shadow(img, [x, y, x + w, y + h], 20, 150, (0, 12))
        m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w, h], 20, fill=255); img.paste(im.convert('RGBA'), (x, y), m)
    d = ImageDraw.Draw(img)
    d.text((70, 120), 'Album Motion', font=font(84, True), fill=(255, 255, 255)); d.text((70, 214), 'Studio', font=font(84, True), fill=PINK)
    d.text((72, 340), 'Capa estática → Apple Music Album Motion Art', font=font(30), fill=(255, 210, 232))
    d.text((72, 392), 'Camadas · keyframes · efeitos · PSD · 3000² e 4K · loop perfeito', font=font(24), fill=(200, 180, 220))
    d.text((72, 436), 'Validação automática · skill e agente de IA', font=font(24), fill=(200, 180, 220))
    d.rounded_rectangle([72, 520, 440, 572], 26, fill=PINK); d.text((100, 531), 'github.com/monkeyinspace-tech', font=font(22, True), fill=(20, 8, 30))
    img.convert('RGB').save(os.path.join(out, 'social-preview.png'))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default=os.path.join(ROOT, 'docs', 'assets')); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True); tmp = tempfile.mkdtemp(prefix='amstudio_img_')
    try:
        sq, tall = frames(demo_project(tmp), 900)
        where_it_appears(a.out, sq, tall); safe_area(a.out, tall); layers_explainer(a.out, tmp); loop_timeline(a.out, tall); social(a.out, tall)
        print('ok')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
