"""
Generate the C盘清理精灵 application icon.
"""

import os

from PIL import Image, ImageDraw, ImageFont


CANVAS_SIZE = 512
SCALE = 4
SIZE = CANVAS_SIZE * SCALE


def scaled(value):
    return int(value * SCALE)


def load_font(size, bold=True):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return ImageFont.truetype(candidate, scaled(size))
    return ImageFont.load_default()


def vertical_gradient(size, top_color, bottom_color):
    width, height = size
    image = Image.new("RGBA", size)
    pixels = image.load()
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(
            int(top_color[index] * (1 - ratio) + bottom_color[index] * ratio)
            for index in range(4)
        )
        for x in range(width):
            pixels[x, y] = color
    return image


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def paste_rounded(base, box, radius, top_color, bottom_color):
    x1, y1, x2, y2 = [scaled(value) for value in box]
    width = x2 - x1
    height = y2 - y1
    gradient = vertical_gradient((width, height), top_color, bottom_color)
    base.paste(gradient, (x1, y1), rounded_mask((width, height), scaled(radius)))


def draw_sparkle(draw, center, radius, fill):
    cx, cy = [scaled(value) for value in center]
    r = scaled(radius)
    points = [
        (cx, cy - r),
        (cx + r // 4, cy - r // 4),
        (cx + r, cy),
        (cx + r // 4, cy + r // 4),
        (cx, cy + r),
        (cx - r // 4, cy + r // 4),
        (cx - r, cy),
        (cx - r // 4, cy - r // 4),
    ]
    draw.polygon(points, fill=fill)


def create_icon():
    os.makedirs("icons", exist_ok=True)

    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Soft shadow.
    draw.rounded_rectangle(
        (scaled(56), scaled(72), scaled(468), scaled(484)),
        radius=scaled(92),
        fill=(6, 83, 76, 72),
    )

    # App tile background.
    paste_rounded(
        image,
        (44, 36, 468, 460),
        96,
        (16, 184, 166, 255),
        (47, 200, 120, 255),
    )
    draw.rounded_rectangle(
        (scaled(64), scaled(54), scaled(448), scaled(438)),
        radius=scaled(82),
        outline=(255, 255, 255, 52),
        width=scaled(5),
    )

    # Inner glass panel.
    draw.rounded_rectangle(
        (scaled(118), scaled(112), scaled(394), scaled(388)),
        radius=scaled(62),
        fill=(235, 255, 250, 58),
        outline=(255, 255, 255, 96),
        width=scaled(5),
    )

    # Water drop body.
    drop_mask = Image.new("L", (SIZE, SIZE), 0)
    drop_draw = ImageDraw.Draw(drop_mask)
    drop_draw.polygon(
        [
            (scaled(256), scaled(120)),
            (scaled(370), scaled(292)),
            (scaled(256), scaled(405)),
            (scaled(142), scaled(292)),
        ],
        fill=255,
    )
    drop_draw.ellipse((scaled(140), scaled(168), scaled(372), scaled(400)), fill=255)
    drop_gradient = vertical_gradient(
        (SIZE, SIZE),
        (232, 255, 251, 245),
        (58, 228, 201, 245),
    )
    image.paste(drop_gradient, (0, 0), drop_mask)
    draw.line(
        [
            (scaled(256), scaled(120)),
            (scaled(370), scaled(292)),
            (scaled(256), scaled(405)),
            (scaled(142), scaled(292)),
            (scaled(256), scaled(120)),
        ],
        fill=(255, 255, 255, 150),
        width=scaled(5),
        joint="curve",
    )
    draw.arc(
        (scaled(156), scaled(186), scaled(356), scaled(378)),
        start=204,
        end=330,
        fill=(255, 255, 255, 150),
        width=scaled(7),
    )

    # C drive mark.
    font = load_font(176)
    text = "C"
    text_box = draw.textbbox((0, 0), text, font=font)
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    text_x = (SIZE - text_width) // 2 - scaled(2)
    text_y = scaled(214) - text_height // 2
    draw.text((text_x + scaled(4), text_y + scaled(6)), text, fill=(0, 105, 96, 88), font=font)
    draw.text((text_x, text_y), text, fill=(255, 255, 255, 245), font=font)

    # Small clean badge.
    draw.rounded_rectangle(
        (scaled(316), scaled(326), scaled(420), scaled(410)),
        radius=scaled(24),
        fill=(255, 255, 255, 235),
    )
    draw.line(
        [
            (scaled(342), scaled(370)),
            (scaled(364), scaled(392)),
            (scaled(398), scaled(348)),
        ],
        fill=(18, 176, 132, 255),
        width=scaled(12),
        joint="curve",
    )
    draw_sparkle(draw, (142, 144), 22, (255, 255, 255, 210))
    draw_sparkle(draw, (394, 126), 15, (255, 255, 255, 170))

    image = image.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)

    png_path = os.path.join("icons", "cleaner.png")
    image.save(png_path)
    print(f"已创建PNG图标: {os.path.abspath(png_path)}")

    ico_path = os.path.join("icons", "cleaner.ico")
    image.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"已创建ICO图标: {os.path.abspath(ico_path)}")


if __name__ == "__main__":
    create_icon()
