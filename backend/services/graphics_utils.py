import glob
import os
import random
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageStat


# ===== 亮度 / 顏色相關 =====


def estimate_brightness(img: Image.Image) -> float:
    """估計整張圖的亮度，0~255，數字越大越亮。"""
    small = img.resize((64, 64)).convert("RGB")
    pixels = list(small.getdata())
    if not pixels:
        return 128.0
    total = 0.0
    for r, g, b in pixels:
        total += 0.2126 * r + 0.7152 * g + 0.0722 * b
    return total / len(pixels)


def compute_luminance(rgb: Tuple[int, int, int]) -> float:
    """計算單一顏色的亮度（0~255，用和估算背景差不多的公式）。"""
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def adjust_color_for_bg(
    base_rgba: Tuple[int, int, int, int],
    brightness: float,
    prefer_light: bool = False,
) -> Tuple[int, int, int, int]:
    """
    依背景亮度調整顏色：
    - 暗背景：把顏色往白色拉，變亮
    - 亮背景：把顏色整體變深
    """
    r, g, b, a = base_rgba

    if brightness < 110:
        # 背景偏暗 → 用亮一點的字
        factor = 0.6 if prefer_light else 0.5
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
    elif brightness > 190:
        # 背景偏亮 → 用深一點的字
        factor = 0.6
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
    # 中間亮度就維持原色

    return (
        max(0, min(255, r)),
        max(0, min(255, g)),
        max(0, min(255, b)),
        a,
    )


def pick_text_color(
    base_rgba: Tuple[int, int, int, int],
    bg_brightness: float,
    prefer_light: bool = False,
) -> Tuple[int, int, int, int]:
    """
    1. 先用 adjust_color_for_bg 做一次基礎調整
    2. 再檢查對比，不夠就強制改成黑或白
    """
    r, g, b, a = adjust_color_for_bg(base_rgba, bg_brightness, prefer_light)
    text_lum = compute_luminance((r, g, b))

    MIN_DIFF = 80  # 對比門檻，可以自己再調整大一點/小一點

    # 如果文字亮度跟背景亮度差太小 → 對比不足
    if abs(text_lum - bg_brightness) < MIN_DIFF:
        if bg_brightness >= 128:
            # 背景偏亮 → 直接用接近黑色的字
            r, g, b = 20, 20, 20
        else:
            # 背景偏暗 → 直接用接近白色的字
            r, g, b = 245, 245, 245

    return (r, g, b, a)


def pick_stroke_color(text_rgba: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """
    根據文字顏色自動選描邊顏色：
    - 字很亮 → 用深色描邊
    - 字很暗 → 用白色描邊
    """
    r, g, b, _ = text_rgba
    lum = compute_luminance((r, g, b))

    if lum > 150:
        # 亮字 → 深描邊
        return (0, 0, 0, 255)
    else:
        # 暗字 → 亮描邊
        return (255, 255, 255, 255)


# ===== 版面配置 / 背景區塊複雜度 =====


def region_complexity(img: Image.Image, box: Tuple[int, int, int, int]) -> float:
    """
    估計某個矩形區域的複雜度：
    這裡用亮度標準差，愈大代表細節愈多（不適合放字）
    """
    x1, y1, x2, y2 = box
    crop = img.crop((int(x1), int(y1), int(x2), int(y2))).convert("L")
    stat = ImageStat.Stat(crop)
    if not stat.stddev:
        return 0.0
    return float(stat.stddev[0])


def pick_best_layout(bg: Image.Image, available_layouts: List[str]) -> str:
    """
    根據背景圖各區塊的「乾淨程度」來挑 layout：
    複雜度最小的區域，就是最適合放字的 layout。
    """
    width, height = bg.size

    # 每個 layout 可能用到的主要文字區域（可以之後再微調）
    regions = {
        "center": [
            (width * 0.15, height * 0.28, width * 0.85, height * 0.65),
        ],
        "top_bottom": [
            (width * 0.15, height * 0.10, width * 0.85, height * 0.28),  # 上面標題
            (width * 0.15, height * 0.60, width * 0.85, height * 0.88),  # 下面副標
        ],
        "left_block": [
            (width * 0.08, height * 0.20, width * 0.55, height * 0.80),
        ],
        "vertical": [
            (width * 0.70, height * 0.15, width * 0.94, height * 0.82),
        ],
        "diagonal": [
            (width * 0.18, height * 0.25, width * 0.82, height * 0.70),
        ],
    }

    best_layout = None
    best_score = None

    for layout, boxes in regions.items():
        if layout not in available_layouts:
            continue

        scores = []
        for box in boxes:
            scores.append(region_complexity(bg, box))

        if not scores:
            continue

        avg_score = sum(scores) / len(scores)

        if best_score is None or avg_score < best_score:
            best_score = avg_score
            best_layout = layout

    if best_layout:
        return best_layout

    # 萬一都失敗，就退回原本的隨機
    return random.choice(available_layouts)


# ===== 畫文字相關 =====


def draw_lines_center(
    draw: ImageDraw.ImageDraw,
    lines: List[str],
    font: ImageFont.ImageFont,
    center_x: int,
    start_y: int,
    line_spacing: int,
    fill: Tuple[int, int, int, int],
    stroke_width: int = 0,
    stroke_fill: Tuple[int, int, int, int] | None = None,
) -> int:
    """多行置中，回傳最後一行畫完後的 y。"""
    y = start_y
    for line in lines:
        if not line:
            continue
        bbox = draw.textbbox((0, 0), line, font=font,
                             stroke_width=stroke_width)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = center_x - text_w // 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        y += text_h + line_spacing
    return y


def draw_lines_left(
    draw: ImageDraw.ImageDraw,
    lines: List[str],
    font: ImageFont.ImageFont,
    start_x: int,
    start_y: int,
    line_spacing: int,
    fill: Tuple[int, int, int, int],
    stroke_width: int = 0,
    stroke_fill: Tuple[int, int, int, int] | None = None,
) -> int:
    """多行靠左。"""
    y = start_y
    for line in lines:
        if not line:
            continue
        bbox = draw.textbbox((0, 0), line, font=font,
                             stroke_width=stroke_width)
        text_h = bbox[3] - bbox[1]
        draw.text(
            (start_x, y),
            line,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        y += text_h + line_spacing
    return y


def draw_vertical_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    x: int,
    start_y: int,
    line_spacing: int,
    fill: Tuple[int, int, int, int],
    stroke_width: int = 0,
    stroke_fill: Tuple[int, int, int, int] | None = None,
) -> int:
    """直書，一個字一行。"""
    y = start_y
    for ch in text:
        if ch.isspace():
            continue
        bbox = draw.textbbox((0, 0), ch, font=font, stroke_width=stroke_width)
        text_h = bbox[3] - bbox[1]
        draw.text(
            (x, y),
            ch,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        y += text_h + line_spacing
    return y


def measure_vertical_text_height(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    line_spacing: int,
    stroke_width: int = 0,
) -> int:
    """計算直書文字的總高度，方便做垂直置中。"""
    total = 0
    first_char = True
    for ch in text:
        if ch.isspace():
            continue
        bbox = draw.textbbox((0, 0), ch, font=font, stroke_width=stroke_width)
        text_h = bbox[3] - bbox[1]
        if not first_char:
            total += line_spacing
        total += text_h
        first_char = False
    return total


# ===== 貼紙相關 =====


def maybe_add_sticker(bg: Image.Image, sticker_dir: str) -> None:
    """
    如果指定資料夾下有 png/webp，就隨機挑一張貼在四個角其中一個。
    """
    if not os.path.isdir(sticker_dir):
        return

    candidates = [
        p for p in glob.glob(os.path.join(sticker_dir, "*.*"))
        if p.lower().endswith((".png", ".webp"))
    ]
    if not candidates:
        return

    path = random.choice(candidates)
    try:
        sticker = Image.open(path).convert("RGBA")
    except Exception:
        return

    max_size = int(bg.width * 0.18)
    sticker.thumbnail((max_size, max_size), Image.LANCZOS)

    corner = random.choice(["tl", "tr", "bl", "br"])
    margin = int(bg.width * 0.03)

    if corner == "tl":
        pos = (margin, margin)
    elif corner == "tr":
        pos = (bg.width - sticker.width - margin, margin)
    elif corner == "bl":
        pos = (margin, bg.height - sticker.height - margin)
    else:
        pos = (
            bg.width - sticker.width - margin,
            bg.height - sticker.height - margin,
        )

    bg.alpha_composite(sticker, dest=pos)


def add_snow_effect(img: Image.Image) -> None:
    """
    在圖片上畫出隨機分佈的半透明雪花。
    """
    # 建立一個可以用來畫半透明圖層的物件
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = img.size

    # 雪花數量，隨機 100~200 顆
    num_flakes = random.randint(100, 200)

    for _ in range(num_flakes):
        x = random.randint(0, width)
        y = random.randint(0, height)
        # 雪花大小不一 (半徑 2~6)
        radius = random.randint(2, 6)
        # 透明度隨機 (150~230)，營造遠近感 (255是不透明)
        alpha = random.randint(150, 230)

        draw.ellipse(
            (x, y, x + radius, y + radius),
            fill=(255, 255, 255, alpha)
        )

    # 將雪花圖層疊加到原圖上
    img.alpha_composite(overlay)
