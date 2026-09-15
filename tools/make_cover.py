"""Generate a drkds module cover image (the Apps Store thumbnail).

560x340 PNG, the store's usual cover size. This is a TITLE CARD, not a
screenshot: it carries the module name, its one-line summary and the suite
mark. It never depicts functionality, so it cannot misrepresent what the
module does. Real screenshots belong in the description page and must be
captured from a working instance.

Usage: make_cover.py <module_dir> [out_path]
Reads name and summary straight from the module's __manifest__.py.
"""
import ast
import os
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

W, H = 560, 340
SCALE = 2
BRAND_TOP = (24, 58, 92)
BRAND_BOTTOM = (13, 32, 54)
ACCENT = (232, 146, 42)
TITLE = (255, 255, 255)
SUB = (183, 198, 214)
FOOT = (138, 157, 176)

FONTS = {
    "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"],
    "reg": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"],
}


def font(kind, px):
    for p in FONTS[kind]:
        try:
            return ImageFont.truetype(p, px)
        except OSError:
            continue
    return ImageFont.load_default()


def manifest(module_dir):
    path = os.path.join(module_dir, "__manifest__.py")
    data = ast.literal_eval(open(path).read())
    return data.get("name", os.path.basename(module_dir)), data.get("summary", "")


def make(module_dir, out_path=None):
    name, summary = manifest(module_dir)
    out_path = out_path or os.path.join(
        module_dir, "static", "description", "cover.png"
    )
    w, h = W * SCALE, H * SCALE
    img = Image.new("RGB", (w, h), BRAND_TOP)

    # vertical gradient
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        grad.putpixel((0, y), tuple(
            round(BRAND_TOP[i] + (BRAND_BOTTOM[i] - BRAND_TOP[i]) * t)
            for i in range(3)))
    img.paste(grad.resize((w, h)), (0, 0))
    d = ImageDraw.Draw(img)

    pad = 46 * SCALE
    # accent rule under the title block
    d.rectangle([pad, int(h * 0.60), pad + 96 * SCALE, int(h * 0.60) + 5 * SCALE],
                fill=ACCENT)

    # title, wrapped, shrinking until it fits above the rule
    size = 40 * SCALE
    while size > 16 * SCALE:
        f = font("bold", size)
        chars = max(14, int((w - 2 * pad) / (size * 0.56)))
        lines = textwrap.wrap(name, width=chars)[:3]
        line_h = int(size * 1.22)
        if len(lines) * line_h <= h * 0.60 - pad - 12 * SCALE:
            break
        size -= 2 * SCALE
    y = int(h * 0.60) - len(lines) * line_h - 16 * SCALE
    for ln in lines:
        d.text((pad, y), ln, font=f, fill=TITLE)
        y += line_h

    # summary below the rule
    fs = font("reg", 17 * SCALE)
    sy = int(h * 0.60) + 22 * SCALE
    for ln in textwrap.wrap(summary, width=62)[:3]:
        d.text((pad, sy), ln, font=fs, fill=SUB)
        sy += int(20 * SCALE * 1.35)

    # footer mark
    ff = font("reg", 14 * SCALE)
    d.text((pad, h - pad + 2 * SCALE),
           "drkds  ·  Odoo 19 Community  ·  LGPL-3", font=ff, fill=FOOT)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.resize((W, H), Image.LANCZOS).save(out_path, "PNG", optimize=True)
    return out_path


if __name__ == "__main__":
    print("wrote", make(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
