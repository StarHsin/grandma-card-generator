import re
from typing import List
from PIL import Image, ImageDraw, ImageFont, ImageStat, ImageEnhance

# 簡單移除 emoji，用來畫在圖片上的文字
# （瀏覽器顯示文字時還是有 emoji，因為那邊用的是原始文字）
EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF]",
    flags=re.UNICODE,
)


def remove_emoji(text: str) -> str:
    """移除字串中的 emoji，避免繪製文字時字型畫不出來。"""
    return EMOJI_PATTERN.sub("", text)


def split_text_to_lines(text: str, max_chars: int) -> List[str]:
    """很粗略地按照字數切行（中文也適用）。"""
    text = text.strip()
    if not text:
        return []
    return [text[i: i + max_chars] for i in range(0, len(text), max_chars)]


def apply_deep_fry(img: Image.Image) -> Image.Image:
    """
    彩蛋：電子包漿特效（高飽和、高對比、過度銳化）。
    模擬那種被轉傳了幾萬次的失真感。
    """
    # 1. 飽和度爆表
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(3.0)  # 顏色超豔

    # 2. 對比度拉高
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # 3. 銳利度爆表 (出現噪點)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(10.0)

    return img


TITLE_MAX_CHARS = 10
SUBTITLE_MAX_CHARS = 12
FOOTER_MAX_CHARS = 18  # 目前不畫 footer，但保留常數方便之後擴充
