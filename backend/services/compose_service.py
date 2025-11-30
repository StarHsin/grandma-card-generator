import base64
import glob
import io
import os
import random
import re
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageStat


# 簡單移除 emoji，用來畫在圖片上的文字
# （瀏覽器顯示文字時還是有 emoji，因為那邊用的是原始文字）
EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF]",
    flags=re.UNICODE,
)


def remove_emoji(text: str) -> str:
    return EMOJI_PATTERN.sub("", text)


def split_text_to_lines(text: str, max_chars: int) -> List[str]:
    """很粗略地按照字數切行（中文也適用）"""
    text = text.strip()
    if not text:
        return []
    return [text[i: i + max_chars] for i in range(0, len(text), max_chars)]


TITLE_MAX_CHARS = 12
SUBTITLE_MAX_CHARS = 20
FOOTER_MAX_CHARS = 24  # 目前不畫 footer，但保留常數方便之後擴充


class ComposeService:
    def __init__(self, background_base_dir: str, font_path: str | None = None):
        self.background_base_dir = background_base_dir
        self.font_path = font_path

        # 不同主題的基礎顏色（之後再依背景亮度微調）
        self.theme_title_colors = {
            "morning": (180, 40, 30, 255),          # 暖紅
            "health": (22, 120, 60, 255),           # 綠色
            "life": (40, 80, 140, 255),             # 深藍
            "festival_newyear": (200, 30, 30, 255),
            "festival_christmas": (190, 40, 40, 255),
            "festival_lantern": (200, 120, 20, 255),
            "festival_midautumn": (160, 120, 40, 255),
            "festival_common": (160, 60, 120, 255),
        }

        # assets root, 給貼紙用
        self.assets_root = os.path.dirname(self.background_base_dir)
        self.sticker_dir = os.path.join(self.assets_root, "stickers")

        # layout 設定
        self.layout_config = {
            "center": {"name": "經典置中"},
            "top_bottom": {"name": "上下分佈"},
            "left_block": {"name": "左側文字"},
            "diagonal": {"name": "斜斜標題"},
            "vertical": {"name": "直書標題"},
        }
        self.available_layouts = list(self.layout_config.keys())

    # ===== 共用工具 =====

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if self.font_path and os.path.exists(self.font_path):
            try:
                return ImageFont.truetype(self.font_path, size)
            except Exception:
                # fallback
                pass
        return ImageFont.load_default()

    def _choose_background(self, theme: str) -> Image.Image:
        theme_dir = os.path.join(self.background_base_dir, theme)
        pattern = os.path.join(theme_dir, "*.*")
        candidates = glob.glob(pattern)

        if not candidates:
            img = Image.new("RGBA", (1024, 1024), (255, 240, 220, 255))
            return img

        img_path = random.choice(candidates)
        img = Image.open(img_path).convert("RGBA")
        img = img.resize((1024, 1024))
        return img

    def _estimate_brightness(self, img: Image.Image) -> float:
        """估計整張圖的亮度，0~255，數字越大越亮"""
        small = img.resize((64, 64)).convert("RGB")
        pixels = list(small.getdata())
        if not pixels:
            return 128.0
        total = 0.0
        for r, g, b in pixels:
            total += 0.2126 * r + 0.7152 * g + 0.0722 * b
        return total / len(pixels)

    def _compute_luminance(self, rgb):
        """計算單一顏色的亮度（0~255，用和估算背景差不多的公式）"""
        r, g, b = rgb
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _pick_text_color(
        self,
        base_rgba,
        bg_brightness: float,
        prefer_light: bool = False,
    ):
        """
        1. 先用原本的 _adjust_color_for_bg 做一次基礎調整
        2. 再檢查對比，不夠就強制改成黑或白
        """
        # 先沿用你原本的調整邏輯
        r, g, b, a = self._adjust_color_for_bg(
            base_rgba, bg_brightness, prefer_light)
        text_lum = self._compute_luminance((r, g, b))

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

    def _pick_stroke_color(self, text_rgba):
        """
        根據文字顏色自動選描邊顏色：
        - 字很亮 → 用深色描邊
        - 字很暗 → 用白色描邊
        """
        r, g, b, _ = text_rgba
        lum = self._compute_luminance((r, g, b))

        if lum > 150:
            # 亮字 → 深描邊
            return (0, 0, 0, 220)
        else:
            # 暗字 → 亮描邊
            return (255, 255, 255, 220)

    def _region_complexity(self, img: Image.Image, box: Tuple[int, int, int, int]) -> float:
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

    def _pick_best_layout(self, bg: Image.Image) -> str:
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
            if layout not in self.available_layouts:
                continue

            scores = []
            for box in boxes:
                scores.append(self._region_complexity(bg, box))

            if not scores:
                continue

            avg_score = sum(scores) / len(scores)

            if best_score is None or avg_score < best_score:
                best_score = avg_score
                best_layout = layout

        if best_layout:
            return best_layout

        # 萬一都失敗，就退回原本的隨機
        return random.choice(self.available_layouts)

    def _adjust_color_for_bg(
        self,
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

    def _draw_lines_center(
        self,
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
        """多行置中，回傳最後一行畫完後的 y"""
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

    def _draw_lines_left(
        self,
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
        """多行靠左"""
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

    def _draw_vertical_text(
        self,
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
        """直書，一個字一行"""
        y = start_y
        for ch in text:
            if ch.isspace():
                continue
            bbox = draw.textbbox((0, 0), ch, font=font,
                                 stroke_width=stroke_width)
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

    def _maybe_add_sticker(self, bg: Image.Image) -> None:
        """
        如果 assets/stickers 下有 png/webp，就隨機挑一張貼在四個角其中一個
        """
        if not os.path.isdir(self.sticker_dir):
            return

        candidates = [
            p for p in glob.glob(os.path.join(self.sticker_dir, "*.*"))
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

    def _get_title_color(self, theme: str) -> Tuple[int, int, int, int]:
        return self.theme_title_colors.get(theme, (180, 40, 30, 255))

    # ===== 對外主方法 =====

    def compose_image(
        self,
        theme: str,
        title: str,
        subtitle: str,
        footer: str,
        layout: str | None = None,
    ) -> str:
        """
        回傳 base64 encoded PNG 字串

        - layout 為 None 或 "auto" 時，會在 available_layouts 之間隨機。
        - 目前只畫 title + subtitle，不畫 footer。
        - 圖片上的文字不含 emoji（先移除避免字型畫不出來）。
        """

        # 先把 emoji 拿掉，再畫到圖片上
        title = remove_emoji(title)
        subtitle = remove_emoji(subtitle)

        bg = self._choose_background(theme)
        width, height = bg.size

        # 統一的安全邊界，避免文字太貼近圖片邊緣
        safe_margin_x = int(width * 0.06)
        safe_margin_y = int(height * 0.06)

        center_x = width // 2

        # 根據背景估計亮度，調整字色
        brightness = self._estimate_brightness(bg)
        base_title = self._get_title_color(theme)
        base_subtitle = (60, 60, 60, 255)

        # 用新的方法選顏色：先微調，再強制確保對比
        title_color = self._pick_text_color(base_title, brightness)
        subtitle_color = self._pick_text_color(
            base_subtitle, brightness, prefer_light=True
        )

        # 字型
        title_font_large = self._load_font(90)
        title_font_normal = self._load_font(72)
        subtitle_font = self._load_font(45)

        title_lines = split_text_to_lines(title, max_chars=TITLE_MAX_CHARS)
        subtitle_lines = split_text_to_lines(
            subtitle, max_chars=SUBTITLE_MAX_CHARS
        )

        # 外框 / glow
        stroke_width = 3
        title_stroke = self._pick_stroke_color(title_color)
        subtitle_stroke = self._pick_stroke_color(subtitle_color)

        # 決定實際要用的 layout
        if not layout or layout == "auto" or layout not in self.available_layouts:
            layout = self._pick_best_layout(bg)

        draw = ImageDraw.Draw(bg)

        if layout == "center":
            # 經典置中
            current_y = int(height * 0.28)
            current_y = self._draw_lines_center(
                draw,
                title_lines,
                title_font_large,
                center_x,
                current_y,
                line_spacing=6,
                fill=title_color,
                stroke_width=stroke_width,
                stroke_fill=title_stroke,
            )
            current_y += 10

            self._draw_lines_center(
                draw,
                subtitle_lines,
                subtitle_font,
                center_x,
                current_y,
                line_spacing=6,
                fill=subtitle_color,
                stroke_width=2,
                stroke_fill=title_stroke,
            )

        elif layout == "top_bottom":
            # 上面是標題，下面是副標
            title_y = int(height * 0.14)
            self._draw_lines_center(
                draw,
                title_lines,
                title_font_normal,
                center_x,
                title_y,
                line_spacing=4,
                fill=title_color,
                stroke_width=stroke_width,
                stroke_fill=title_stroke,
            )
            subtitle_y = int(height * 0.62)

            self._draw_lines_center(
                draw,
                subtitle_lines,
                subtitle_font,
                center_x,
                subtitle_y,
                line_spacing=4,
                fill=subtitle_color,
                stroke_width=2,
                stroke_fill=title_stroke,
            )

        elif layout == "left_block":
            # 左側區塊：標題 + 內容都改成直式，靠左排
            margin_x = safe_margin_x
            top_y = safe_margin_y

            # 把多行合併成一串，再做直書；空白字元先拿掉
            vertical_title = "".join(
                ch for ch in "".join(title_lines) if not ch.isspace()
            )
            vertical_subtitle = "".join(
                ch for ch in "".join(subtitle_lines) if not ch.isspace()
            )

            # 標題直書在最左邊
            self._draw_vertical_text(
                draw,
                vertical_title,
                title_font_normal,
                x=margin_x,
                start_y=top_y,
                line_spacing=4,
                fill=title_color,
                stroke_width=stroke_width,
                stroke_fill=title_stroke,
            )

            # 副標直書放在右邊一點的位置，形成兩欄直式
            subtitle_x = margin_x + int(width * 0.06)
            self._draw_vertical_text(
                draw,
                vertical_subtitle,
                subtitle_font,
                x=subtitle_x,
                start_y=top_y,
                line_spacing=4,
                fill=subtitle_color,
                stroke_width=2,
                stroke_fill=title_stroke,
            )

        elif layout == "vertical":
            # 直書標題 + 內容都靠右排成兩欄
            top_y = safe_margin_y

            # 估一個中文字寬度，避免貼到右邊
            sample_char = "永"
            title_bbox = draw.textbbox(
                (0, 0), sample_char, font=title_font_normal, stroke_width=stroke_width)
            title_char_w = title_bbox[2] - title_bbox[0]

            subtitle_bbox = draw.textbbox(
                (0, 0), sample_char, font=subtitle_font, stroke_width=2)
            subtitle_char_w = subtitle_bbox[2] - subtitle_bbox[0]

            # 最右邊放標題，再往左放副標
            title_x = width - safe_margin_x - title_char_w
            column_gap = max(int(width * 0.04),
                             subtitle_char_w + int(width * 0.01))
            subtitle_x = title_x - column_gap

            vertical_title = "".join(ch for ch in "".join(
                title_lines) if not ch.isspace())
            vertical_subtitle = "".join(ch for ch in "".join(
                subtitle_lines) if not ch.isspace())

            self._draw_vertical_text(
                draw,
                vertical_title,
                title_font_normal,
                x=title_x,
                start_y=top_y,
                line_spacing=4,
                fill=title_color,
                stroke_width=stroke_width,
                stroke_fill=title_stroke,
            )

            self._draw_vertical_text(
                draw,
                vertical_subtitle,
                subtitle_font,
                x=subtitle_x,
                start_y=top_y,
                line_spacing=4,
                fill=subtitle_color,
                stroke_width=2,
                stroke_fill=title_stroke,
            )

        # 最後可選地加一張貼紙
        self._maybe_add_sticker(bg)

        # 轉成 base64
        buffer = io.BytesIO()
        bg.convert("RGB").save(buffer, format="PNG")
        base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return base64_str
