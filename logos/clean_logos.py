"""
Bespoke logo clean-up.

Back up every PNG to logos/originals/ (only if not already backed up),
then apply per-logo cleanup rules so the builder cards render without
distracting padding/borders.

Re-running is safe: each clean step reads from logos/originals/.
"""
import shutil
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
ORIG = HERE / "originals"
ORIG.mkdir(exist_ok=True)


def backup_all():
    for p in HERE.glob("*.png"):
        if p.name.endswith(".bak"):
            continue
        target = ORIG / p.name
        if not target.exists():
            shutil.copy2(p, target)


def source(name: str) -> Path:
    """Always read from the preserved original."""
    return ORIG / name


# ── DARE: fill transparent surround AND pad canvas with the inner tile's
#         exact background colour (not pure black) so there is no visible
#         seam between original tile and padding.
def clean_dare():
    src = source("dare.png")
    if not src.exists():
        print("  dare.png: no original, skipped")
        return
    img = Image.open(src).convert("RGBA")
    px = img.load()
    w, h = img.size
    # Sample the inner tile background colour: walk inward from the centre
    # along the horizontal midline until we hit the first opaque pixel.
    cy = h // 2
    x = 0
    while x < w and px[x, cy][3] < 255:
        x += 1
    bg = px[min(x + 10, w - 1), cy][:3] if x < w else (0, 0, 0)
    bg_rgba = (*bg, 255)
    for y in range(h):
        for x in range(w):
            if px[x, y][3] < 255:
                px[x, y] = bg_rgba
    target_aspect = 2.6
    new_w = max(w, int(h * target_aspect))
    if new_w > w:
        padded = Image.new("RGBA", (new_w, h), bg_rgba)
        padded.paste(img, ((new_w - w) // 2, 0))
        img = padded
    img.save(HERE / "dare.png")
    print(f"  dare.png: filled+padded with bg {bg} to {img.size}")


# ── STROUD: detect & crop inside the green frame border ────────────────────
def is_green_border(px):
    r, g, b, a = px
    # green-dominant pixels: G clearly higher than R and B, G > 100
    return a > 200 and g > 100 and g > r + 30 and g > b + 30


def clean_stroud():
    src = source("stroud.png")
    if not src.exists():
        print("  stroud.png: no original, skipped")
        return
    img = Image.open(src).convert("RGBA")
    w, h = img.size
    px = img.load()

    # Walk inward from each edge until a row/column is mostly non-green
    def row_is_green(y):
        return sum(1 for x in range(w) if is_green_border(px[x, y])) > w * 0.5

    def col_is_green(x):
        return sum(1 for y in range(h) if is_green_border(px[x, y])) > h * 0.5

    top = 0
    while top < h and row_is_green(top):
        top += 1
    bottom = h - 1
    while bottom > top and row_is_green(bottom):
        bottom -= 1
    left = 0
    while left < w and col_is_green(left):
        left += 1
    right = w - 1
    while right > left and col_is_green(right):
        right -= 1

    inset = 2
    bbox = (
        min(left + inset, w),
        min(top + inset, h),
        max(right - inset + 1, 0),
        max(bottom - inset + 1, 0),
    )
    cropped = img.crop(bbox)

    # Auto-trim near-white margins so the cube + wordmark sit centred.
    # Walks edges inward; tolerates a handful of antialias-noise outlier
    # pixels (frame-corner remnants) by requiring >2% non-white density
    # before counting a row/col as "content".
    cw, ch = cropped.size
    cpx = cropped.load()
    def is_white(p):
        r, g, b, a = p
        return a < 10 or (r >= 235 and g >= 235 and b >= 235)
    row_thresh = max(3, int(cw * 0.02))
    col_thresh = max(3, int(ch * 0.02))
    def row_has_content(y):
        return sum(1 for x in range(cw) if not is_white(cpx[x, y])) > row_thresh
    def col_has_content(x):
        return sum(1 for y in range(ch) if not is_white(cpx[x, y])) > col_thresh
    top2 = 0
    while top2 < ch and not row_has_content(top2):
        top2 += 1
    bottom2 = ch - 1
    while bottom2 > top2 and not row_has_content(bottom2):
        bottom2 -= 1
    left2 = 0
    while left2 < cw and not col_has_content(left2):
        left2 += 1
    right2 = cw - 1
    while right2 > left2 and not col_has_content(right2):
        right2 -= 1
    if left2 < right2 and top2 < bottom2:
        cropped = cropped.crop((left2, top2, right2 + 1, bottom2 + 1))

    cropped.save(HERE / "stroud.png")
    print(f"  stroud.png: {img.size} -> {cropped.size} (cube + wordmark, centred)")


def main():
    backup_all()
    print("Backups in:", ORIG)
    clean_dare()
    clean_stroud()


if __name__ == "__main__":
    main()
