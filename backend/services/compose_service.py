import base64
import glob
import io
import os
import random
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont


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

        # layout 設定（如果未來要用 JSON，可以直接把這份 dict dump 出去）
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
            # 人眼感知亮度
            total += 0.2126 * r + 0.7152 * g + 0.0722 * b
        return total / len(pixels)

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
            pos = (bg.width - sticker.width - margin,
                   bg.height - sticker.height - margin)

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
        """
        bg = self._choose_background(theme)
        width, height = bg.size
        center_x = width // 2

        # 根據背景估計亮度，調整字色
        brightness = self._estimate_brightness(bg)
        base_title = self._get_title_color(theme)
        base_subtitle = (60, 60, 60, 255)

        title_color = self._adjust_color_for_bg(base_title, brightness)
        subtitle_color = self._adjust_color_for_bg(
            base_subtitle, brightness, prefer_light=True
        )

        # 字型
        title_font_large = self._load_font(80)
        title_font_normal = self._load_font(64)
        subtitle_font = self._load_font(40)

        title_lines = split_text_to_lines(title, max_chars=TITLE_MAX_CHARS)
        subtitle_lines = split_text_to_lines(
            subtitle, max_chars=SUBTITLE_MAX_CHARS
        )

        # 畫外框當作 glow
        stroke_width = 3
        stroke_fill = (255, 255, 255, 210)

        # 決定實際要用的 layout
        if not layout or layout == "auto" or layout not in self.available_layouts:
            layout = random.choice(self.available_layouts)

        # 有些 layout 要直接在 bg 上畫
        if layout in ("center", "top_bottom", "left_block", "vertical"):
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
                stroke_fill=stroke_fill,
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
                stroke_fill=(0, 0, 0, 160),
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
                stroke_fill=stroke_fill,
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
                stroke_fill=(0, 0, 0, 160),
            )

        elif layout == "left_block":
            # 左側區塊
            margin_x = int(width * 0.12)
            title_y = int(height * 0.22)
            subtitle_y = title_y + 160

            self._draw_lines_left(
                draw,
                title_lines,
                title_font_normal,
                start_x=margin_x,
                start_y=title_y,
                line_spacing=4,
                fill=title_color,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
            self._draw_lines_left(
                draw,
                subtitle_lines,
                subtitle_font,
                start_x=margin_x,
                start_y=subtitle_y,
                line_spacing=4,
                fill=subtitle_color,
                stroke_width=2,
                stroke_fill=(0, 0, 0, 160),
            )

        elif layout == "vertical":
            # 直書標題靠右，副標在下方
            margin_x = int(width * 0.82)
            top_y = int(height * 0.18)

            self._draw_vertical_text(
                draw,
                "".join(ch for ch in title if not ch.isspace()),
                title_font_normal,
                x=margin_x,
                start_y=top_y,
                line_spacing=4,
                fill=title_color,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )

            subtitle_y = int(height * 0.7)
            self._draw_lines_center(
                draw,
                subtitle_lines,
                subtitle_font,
                center_x,
                subtitle_y,
                line_spacing=4,
                fill=subtitle_color,
                stroke_width=2,
                stroke_fill=(0, 0, 0, 160),
            )

        elif layout == "diagonal":
            # 斜斜的標題：先在小畫布上畫好，再整塊旋轉貼上去
            block_w = int(width * 0.8)
            block_h = int(height * 0.4)
            block = Image.new("RGBA", (block_w, block_h), (0, 0, 0, 0))
            b_draw = ImageDraw.Draw(block)

            block_center_x = block_w // 2
            y = 10
            y = self._draw_lines_center(
                b_draw,
                title_lines,
                title_font_large,
                block_center_x,
                y,
                line_spacing=4,
                fill=title_color,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
            y += 6
            self._draw_lines_center(
                b_draw,
                subtitle_lines,
                subtitle_font,
                block_center_x,
                y,
                line_spacing=4,
                fill=subtitle_color,
                stroke_width=2,
                stroke_fill=(0, 0, 0, 160),
            )

            angle = random.choice([-18, -12, 12, 18])
            rotated = block.rotate(angle, resample=Image.BICUBIC, expand=True)
            bx = (width - rotated.width) // 2
            by = (height - rotated.height) // 2
            bg.alpha_composite(rotated, dest=(bx, by))

        # 最後可選地加一張貼紙
        self._maybe_add_sticker(bg)

        # 轉成 base64
        buffer = io.BytesIO()
        bg.convert("RGB").save(buffer, format="PNG")
        base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return base64_str
