import base64
import glob
import io
import os
import random
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

from .text_utils import (
    remove_emoji,
    split_text_to_lines,
    TITLE_MAX_CHARS,
    SUBTITLE_MAX_CHARS,
    FOOTER_MAX_CHARS,
    apply_deep_fry,
)
from .graphics_utils import (
    estimate_brightness,
    pick_text_color,
    pick_stroke_color,
    pick_best_layout,
    draw_lines_center,
    draw_vertical_text,
    measure_vertical_text_height,
    maybe_add_sticker,
    add_snow_effect,
)


class ComposeService:
    def __init__(self, background_base_dir: str, font_path: str | None = None):
        self.background_base_dir = background_base_dir
        self.font_path = font_path

        # 不同主題的基礎顏色（之後再依背景亮度微調）
        self.theme_title_colors = {
            "morning": (255, 50, 20, 255),          # 暖紅
            "health": (20, 180, 50, 255),           # 綠色
            "life": (30, 100, 200, 255),            # 深藍
            "festival_newyear": (255, 20, 20, 255),
            "festival_christmas": (220, 20, 20, 255),
            "festival_lantern": (255, 150, 0, 255),
            "festival_midautumn": (220, 180, 50, 255),
            "festival_common": (220, 50, 150, 255),
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
        # === [新增] 背景圖映射邏輯 ===
        # 如果是特殊彩蛋，強制借用別人的背景圖
        # 地獄梗 -> 用早安圖 (反差最大)
        # 壞了 -> 用健康圖 (身體健康 vs 系統壞了)
        target_theme = theme
        if theme in ["dark_humor", "broken_egg", "programmer"]:
            target_theme = random.choice(["morning", "life"])

        theme_dir = os.path.join(self.background_base_dir, target_theme)
        pattern = os.path.join(theme_dir, "*.*")
        candidates = glob.glob(pattern)

        if not candidates:
            img = Image.new("RGBA", (1024, 1024), (255, 240, 220, 255))
            return img

        img_path = random.choice(candidates)
        img = Image.open(img_path).convert("RGBA")
        img = img.resize((1024, 1024))
        return img

    def _get_title_color(self, theme: str) -> Tuple[int, int, int, int]:

        # === [新增] 彩蛋 ：工程師專屬綠色 ===
        if theme == "programmer":
            return (0, 255, 0, 255)  # 鮮豔的 Hacker Green

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

        - layout 為 None 或 "auto" 時，會在 available_layouts 之間自動挑選。
        - 目前只畫 title + subtitle，不畫 footer。
        - 圖片上的文字不含 emoji（先移除避免字型畫不出來）。
        """
        # === [新增] 處理 theme 後綴 ===
        # 如果 theme 包含 "_retro"，先把它還原成正常的資料夾名稱來找背景
        real_theme = theme
        if "_retro" in theme:
            real_theme = theme.replace("_retro", "")

        # 先把 emoji 拿掉，再畫到圖片上
        title = remove_emoji(title)
        subtitle = remove_emoji(subtitle)

        bg = self._choose_background(real_theme)
        width, height = bg.size

        # 統一的安全邊界，避免文字太貼近圖片邊緣
        safe_margin_x = int(width * 0.06)
        safe_margin_y = int(height * 0.06)

        center_x = width // 2

        # 根據背景估計亮度，調整字色
        brightness = estimate_brightness(bg)
        base_title = self._get_title_color(real_theme)
        base_subtitle = (60, 60, 60, 255)

        # 用新的方法選顏色：先微調，再強制確保對比
        title_color = pick_text_color(base_title, brightness)
        subtitle_color = pick_text_color(
            base_subtitle, brightness, prefer_light=True
        )

        # 字型
        title_font_large = self._load_font(100)
        title_font_normal = self._load_font(80)
        subtitle_font = self._load_font(45)

        title_lines = split_text_to_lines(title, max_chars=TITLE_MAX_CHARS)
        subtitle_lines = split_text_to_lines(
            subtitle, max_chars=SUBTITLE_MAX_CHARS
        )

        # 外框 / glow
        stroke_width = 6
        title_stroke = pick_stroke_color(title_color)
        subtitle_stroke = pick_stroke_color(subtitle_color)

        # 決定實際要用的 layout
        if not layout or layout == "auto" or layout not in self.available_layouts:
            layout = pick_best_layout(bg, self.available_layouts)

        draw = ImageDraw.Draw(bg)

        if layout == "center":
            # 經典置中
            current_y = int(height * 0.28)
            current_y = draw_lines_center(
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

            draw_lines_center(
                draw,
                subtitle_lines,
                subtitle_font,
                center_x,
                current_y,
                line_spacing=6,
                fill=subtitle_color,
                stroke_width=4,
                stroke_fill=title_stroke,
            )

        elif layout == "top_bottom":
            # 上面是標題，下面是副標
            title_y = int(height * 0.14)
            draw_lines_center(
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

            draw_lines_center(
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
            # 左側區塊：標題 + 內容直書在左邊，英文改放下面橫排
            margin_x = safe_margin_x

            # 只挑出要做直書的文字：非 ASCII（中文、全形符號），英文等留給橫排
            title_source = "".join(title_lines)
            subtitle_source = "".join(subtitle_lines)

            vertical_title = "".join(
                ch for ch in title_source
                if not ch.isspace() and ord(ch) >= 128
            )
            vertical_subtitle = "".join(
                ch for ch in subtitle_source
                if not ch.isspace() and ord(ch) >= 128
            )

            # 計算直書標題 / 內容的高度，讓整塊在上下方向置中
            title_block_h = measure_vertical_text_height(
                draw,
                vertical_title,
                title_font_normal,
                line_spacing=4,
                stroke_width=stroke_width,
            )
            subtitle_block_h = measure_vertical_text_height(
                draw,
                vertical_subtitle,
                subtitle_font,
                line_spacing=4,
                stroke_width=2,
            )
            block_h = max(title_block_h, subtitle_block_h)
            available_h = height - 2 * safe_margin_y

            if block_h > 0 and block_h < available_h:
                # 有空間 → 讓整個直書區塊上下置中
                top_y = safe_margin_y + (available_h - block_h) // 2
            else:
                # 太長就從安全邊界開始畫，避免文字跑出圖外
                top_y = safe_margin_y

            # 標題直書在最左邊
            draw_vertical_text(
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

            # 拉大欄距，讓標題跟內容不要太擠
            column_gap = int(width * 0.09)
            subtitle_x = margin_x + column_gap

            # 副標直書放在右邊一點的位置，形成兩欄直式
            draw_vertical_text(
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

            # 額外：把英文集中畫在圖片下方置中，避免英文直書怪怪的
            english_chars = [
                ch
                for ch in f"{title} {subtitle}"
                if ch.isascii() and (ch.isalpha() or ch.isdigit() or ch.isspace())
            ]
            english_text = "".join(english_chars)
            # 把多個空白縮成一個，避免空格亂七八糟
            english_text = " ".join(english_text.split())

            if english_text:
                bbox = draw.textbbox(
                    (0, 0),
                    english_text,
                    font=subtitle_font,
                    stroke_width=2,
                )
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]

                english_x = center_x - text_w // 2
                english_y = height - safe_margin_y - text_h

                draw.text(
                    (english_x, english_y),
                    english_text,
                    font=subtitle_font,
                    fill=subtitle_color,
                    stroke_width=2,
                    stroke_fill=subtitle_stroke,
                )

        elif layout == "vertical":
            # 直書標題 + 內容都靠右排成兩欄
            top_y = safe_margin_y

            # 估一個中文字寬度，避免貼到右邊
            sample_char = "永"
            title_bbox = draw.textbbox(
                (0, 0), sample_char, font=title_font_normal, stroke_width=stroke_width
            )
            title_char_w = title_bbox[2] - title_bbox[0]

            subtitle_bbox = draw.textbbox(
                (0, 0), sample_char, font=subtitle_font, stroke_width=2
            )
            subtitle_char_w = subtitle_bbox[2] - subtitle_bbox[0]

            # 最右邊放標題，再往左放副標
            title_x = width - safe_margin_x - title_char_w
            column_gap = max(int(width * 0.04),
                             subtitle_char_w + int(width * 0.01))
            subtitle_x = title_x - column_gap

            vertical_title = "".join(ch for ch in "".join(
                title_lines) if not ch.isspace())
            vertical_subtitle = "".join(
                ch for ch in "".join(subtitle_lines) if not ch.isspace()
            )

            draw_vertical_text(
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

            draw_vertical_text(
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
        maybe_add_sticker(bg, self.sticker_dir)

        # === [新增] 彩蛋：飄雪特效 ===
        # 觸發條件：主題包含 "christmas" (聖誕節)，或者標題/副標有 "雪" 這個字
        is_christmas = "christmas" in theme
        has_snow_text = "雪" in title or "雪" in subtitle

        if is_christmas or has_snow_text:
            add_snow_effect(bg)

        if "old" in theme or "retro" in theme or "復古" in title:
            bg = apply_deep_fry(bg)

        # 轉成 base64
        buffer = io.BytesIO()
        bg.convert("RGB").save(buffer, format="PNG")
        base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return base64_str
