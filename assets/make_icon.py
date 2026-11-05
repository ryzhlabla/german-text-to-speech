"""Draw the app icon. Run from the project folder: python assets/make_icon.py"""
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 1024
TOP_COLOR = (45, 212, 191)
BOTTOM_COLOR = (15, 118, 110)
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def background():
    """Return a rounded square with a soft top-to-bottom gradient."""
    gradient = Image.new("RGBA", (SIZE, SIZE))
    draw = ImageDraw.Draw(gradient)
    for y in range(SIZE):
        mix = y / (SIZE - 1)
        color = tuple(round(a + (b - a) * mix) for a, b in zip(TOP_COLOR, BOTTOM_COLOR))
        draw.line([(0, y), (SIZE, y)], fill=color)
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=224, fill=255)
    gradient.putalpha(mask)
    return gradient


def main():
    icon = background()
    draw = ImageDraw.Draw(icon)
    # White speech bubble with a tail
    draw.rounded_rectangle([150, 190, 874, 720], radius=150, fill="white")
    draw.polygon([(300, 680), (300, 880), (500, 700)], fill="white")
    # Sound bars inside the bubble
    for x, height in [(300, 130), (404, 270), (512, 370), (620, 270), (724, 130)]:
        draw.rounded_rectangle([x - 34, 455 - height // 2, x + 34, 455 + height // 2], radius=34, fill=BOTTOM_COLOR)

    folder = Path(__file__).parent
    icon.resize((256, 256), Image.LANCZOS).save(folder / "icon.png")
    icon.save(folder / "icon.ico", sizes=ICO_SIZES)


if __name__ == "__main__":
    main()
