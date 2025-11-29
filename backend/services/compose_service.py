import base64
import io
import os
import random
import glob
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


def split_text_to_lines(text: str, max_chars: int) -> list:
    """很粗略地按照字數切行（中文也適用）"""
    text = text.strip()
    if not text:
        return []
    return [text[i: i + max_chars] for i in range(0, len(text), max_chars)]


class ComposeService:
    def __init__(self, background_base_dir: str, font_path: str | None = None):
        self.background_base_dir = background_base_dir
        self.font_path = font_path

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if self.font_path and os.path.exists(self.font_path):
            try:
                return ImageFont.truetype(self.font_path, size)
            except Exception:
                # fallback to default font
                pass
        return ImageFont.load_default()

    def _choose_background(self, theme: str) -> Image.Image:
        theme_dir = os.path.join(self.background_base_dir, theme)
        pattern = os.path.join(theme_dir, "*.*")
        candidates = glob.glob(pattern)

        if not candidates:
            # 如果沒有找到任何圖片，就產生一張純色背景
            img = Image.new("RGBA", (1024, 1024), (255, 240, 220, 255))
            return img

        img_path = random.choice(candidates)
        img = Image.open(img_path).convert("RGBA")
        # 統一 resize 一下，避免太大
        img = img.resize((1024, 1024))
        return img

    def _draw_centered_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.ImageFont,
        center_x: int,
        y: int,
        fill: Tuple[int, int, int, int] = (0, 0, 0, 255),
    ) -> int:
        """在指定 y 位置，把文字置中畫上去，回傳下一行 y 座標"""
        if not text:
            return y

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = center_x - text_width // 2
        draw.text((x, y), text, font=font, fill=fill)
        return y + text_height + 10  # 行距 +10px

    def compose_image(
        self,
        theme: str,
        title: str,
        subtitle: str,
        footer: str,
    ) -> str:
        """
        回傳 base64 encoded PNG 字串
        """
        bg = self._choose_background(theme)
        draw = ImageDraw.Draw(bg)

        width, height = bg.size
        center_x = width // 2

        # 字型設定
        title_font = self._load_font(64)
        subtitle_font = self._load_font(40)
        footer_font = self._load_font(32)

        # 先做一層半透明遮罩，讓文字比較清楚（可選）
        overlay = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [(80, 80), (width - 80, height - 80)],
            fill=(255, 255, 255, 120),
        )
        bg = Image.alpha_composite(bg, overlay)
        draw = ImageDraw.Draw(bg)

        # 把 subtitle / footer 切行（避免太長）
        subtitle_lines = split_text_to_lines(subtitle, max_chars=15)
        footer_lines = split_text_to_lines(footer, max_chars=18)

        # 排版：大致上 title 在中上方，subtitle 在中間，footer 在下方
        current_y = height // 4

        # title 可以分兩行（如果需要）
        for line in split_text_to_lines(title, max_chars=8):
            current_y = self._draw_centered_text(
                draw, line, title_font, center_x, current_y, fill=(
                    120, 0, 0, 255)
            )

        current_y += 20  # 多留一點空白

        for line in subtitle_lines:
            current_y = self._draw_centered_text(
                draw, line, subtitle_font, center_x, current_y, fill=(
                    60, 60, 60, 255)
            )

        # footer 貼近底部一點
        footer_y = int(height * 0.75)
        for line in footer_lines:
            footer_y = self._draw_centered_text(
                draw, line, footer_font, center_x, footer_y, fill=(
                    90, 90, 90, 255)
            )

        # 轉成 base64
        buffer = io.BytesIO()
        bg.convert("RGB").save(buffer, format="PNG")
        base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return base64_str
