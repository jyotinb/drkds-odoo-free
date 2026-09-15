"""Generate a drkds house-style module icon: 140x140 PNG, rounded square,
brand gradient, a short glyph and a bottom accent bar."""
import sys
from PIL import Image, ImageDraw, ImageFont

BRAND_TOP = (24, 58, 92)      # deep indigo
BRAND_BOTTOM = (13, 32, 54)
ACCENT = (232, 146, 42)       # saffron accent
TEXT = (255, 255, 255)
SIZE = 140
RADIUS = 30
SCALE = 4  # supersample for smooth edges

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _font(px):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, px)
        except OSError:
            continue
    return ImageFont.load_default()


def make(glyph, out_path):
    s = SIZE * SCALE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # vertical gradient body
    grad = Image.new("RGB", (1, s))
    for y in range(s):
        t = y / (s - 1)
        grad.putpixel((0, y), tuple(
            round(BRAND_TOP[i] + (BRAND_BOTTOM[i] - BRAND_TOP[i]) * t) for i in range(3)
        ))
    grad = grad.resize((s, s))

    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, s - 1, s - 1], radius=RADIUS * SCALE, fill=255
    )
    img.paste(grad, (0, 0), mask)

    draw = ImageDraw.Draw(img)

    # accent bar near the bottom, clipped by the rounded mask
    bar = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(bar).rectangle(
        [0, int(s * 0.80), s, int(s * 0.875)], fill=ACCENT + (255,)
    )
    img.paste(bar, (0, 0), Image.composite(bar.split()[3], Image.new("L", (s, s), 0), mask))

    # glyph, auto-sized to fit the width
    glyph = glyph.upper()[:3]
    px = int(s * (0.46 if len(glyph) <= 2 else 0.34))
    font = _font(px)
    while True:
        box = draw.textbbox((0, 0), glyph, font=font)
        if box[2] - box[0] <= s * 0.68 or px <= 12:
            break
        px -= 4
        font = _font(px)
    box = draw.textbbox((0, 0), glyph, font=font)
    draw.text(
        ((s - (box[2] - box[0])) / 2 - box[0],
         (s - (box[3] - box[1])) / 2 - box[1] - s * 0.045),
        glyph, font=font, fill=TEXT,
    )

    img.resize((SIZE, SIZE), Image.LANCZOS).save(out_path, "PNG")


if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2])
    print("wrote", sys.argv[2])
