import json
import os
from dataclasses import dataclass
from typing import Dict, Optional

from google import genai


@dataclass
class ElderCardText:
    title: str
    subtitle: str
    footer: str


class LLMService:
    """
    使用 Gemini API 產生長輩圖文案。
    - 有 GEMINI_API_KEY 或 GOOGLE_API_KEY 就呼叫 Gemini
    - 沒有或出錯則使用內建模板 fallback
    """

    def __init__(self) -> None:
        # 這些是預設模板，會在沒有 LLM 或錯誤時使用
        self.templates: Dict[str, ElderCardText] = {
            "morning": ElderCardText(
                title="早安 祝福滿滿",
                subtitle="新的一天記得多呼吸幾口新鮮空氣，讓心情跟著亮起來。",
                footer="把這份祝福分享給在乎的人，一起元氣滿滿迎接今天 ☀️",
            ),
            "health": ElderCardText(
                title="健康是最大的財富",
                subtitle="少熬夜、多喝水，適度活動筋骨，身體才會跟你當好朋友。",
                footer="想起好久不見的親朋好友，關心一句：最近也要記得照顧自己喔 💕",
            ),
            "life": ElderCardText(
                title="人生慢慢來也沒關係",
                subtitle="偶爾停下腳步，看看身邊的人、身邊的風景，也是種收穫。",
                footer="把這張圖傳給懂你的人，一起好好過生活 🌿",
            ),
            "festival_newyear": ElderCardText(
                title="新年快樂 福氣滿滿",
                subtitle="願你新的一年，平安順心、笑口常開，家人健康闔家團圓。",
                footer="想到誰想一起過好年，就快把祝福傳給他吧 🧧",
            ),
            "festival_christmas": ElderCardText(
                title="聖誕快樂 平安喜樂",
                subtitle="願溫暖的燈火，照亮你與家人的笑容與心。",
                footer="把這份小小的祝福傳出去，讓聖誕更有味道 🎄",
            ),
        }

        # SDK 會自動讀 GEMINI_API_KEY 或 GOOGLE_API_KEY，這裡也可以手動讀
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        print("[LLMService] GEMINI_API_KEY loaded:", bool(api_key))

        # ✅ 這裡改成正確的 Client 寫法
        self.client: Optional[genai.Client] = (
            genai.Client(api_key=api_key) if api_key else None
        )

        # 你可以改成適合自己的模型，例如 gemini-2.0-flash / gemini-2.5-flash 等
        self.model_name = "gemini-2.0-flash"

        # 主題 key -> 中文說明（給 prompt 用）
        self.theme_descriptions: Dict[str, str] = {
            "morning": "早安、早晨開啟新的一天，溫暖打氣的祝福。",
            "health": "健康、保重身體、注意飲食作息的提醒與祝福。",
            "life": "生活感悟、人生小語，鼓勵放慢腳步、好好生活。",
            "festival_newyear": "農曆新年、新春、過年拜年祝福。",
            "festival_christmas": "聖誕節、雪、禮物、團聚氛圍的祝福。",
            "festival_common": "一般節慶祝福（例如母親節、父親節、紀念日等）。",
            "festival_lantern": "元宵節、提燈籠、吃湯圓、團圓的祝福。",
            "festival_midautumn": "中秋節、賞月、吃月餅、團圓的祝福。",
        }

    # --------- prompt 組裝 ---------

    def _build_prompt(self, theme: str) -> str:
        theme_desc = self.theme_descriptions.get(
            theme, "一般祝福，內容溫暖、正向、適合傳給親友。"
        )

        instructions = f"""
你是一位擅長幫人寫 Line 「長輩圖」祝福文字的文案設計師。
風格要求：
- 使用臺灣常見的繁體中文用語。
- 口吻溫暖、關心、帶一點可愛幽默，但不要太油膩。
- 可以適度使用 emoji，但整體不要超過 3 個。
- 讓長輩看到會想轉傳給朋友或家人的感覺。

輸出結構：
- title：8～15 個字左右，適合作為長輩圖主標題，語氣正向、簡潔有力。
- subtitle：1～2 句，約 25～45 個字，針對主題給出具體的關心或提醒。
- footer：1 句，約 20～35 個字，鼓勵把這張圖分享給某個對象，可以附上 1～2 個 emoji。

主題說明：
{theme_desc}

注意：
- 一律使用繁體中文。
- 不要出現色情、暴力、仇恨或歧視內容。
- 最後「只輸出 JSON」，不要任何多餘解釋或文字。
JSON 格式如下：

{{
  "title": "...",
  "subtitle": "...",
  "footer": "..."
}}

請根據上面的說明，為「{theme}」這個主題產生一組新的祝福文字，不要重複範例內容。
        """.strip()

        few_shot = """
以下是幾個示例，僅供你學習風格，不要直接複製：

[範例 1：morning]
{
  "title": "早安 祝福滿滿",
  "subtitle": "新的一天從微笑開始，深呼吸幾口新鮮空氣，讓心也跟著亮起來。",
  "footer": "想到哪位重要的人，就把這份小小問候傳給他吧 ☀️"
}

[範例 2：health]
{
  "title": "健康是最大的財富",
  "subtitle": "該休息時就好好休息，多喝水、多活動，身體才會陪你走更長遠的路。",
  "footer": "關心自己，也別忘了叮嚀在乎的人一起顧健康 💕"
}

現在請你依照「主題說明」與這些示例的感覺，產生一組全新的 JSON。
        """.strip()

        full_prompt = instructions + "\n\n" + few_shot
        return full_prompt

    # --------- fallback ---------

    def _fallback(self, theme: str) -> ElderCardText:
        if theme in self.templates:
            return self.templates[theme]

        return ElderCardText(
            title="送上暖暖的祝福",
            subtitle="不管今天忙不忙，都別忘了幫自己留一點喘口氣的時間。",
            footer="把這張充滿祝福的小卡，傳給你在乎的人吧 ❤️",
        )

    # --------- 對外主方法 ---------

    def generate_text(self, theme: str) -> ElderCardText:
        """
        對外呼叫：
        - 優先用 Gemini 產生 JSON 再 parse
        - 失敗就回到模板
        """
        if not self.client:
            # 沒有 API key，直接 fallback
            return self._fallback(theme)

        prompt = self._build_prompt(theme)

        try:
            # google-genai 標準用法：
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.6,
                    "max_output_tokens": 400,
                },
            )

            raw_text = response.text.strip()
            print("[LLMService] Gemini raw response:", raw_text)  # debug 用

            data = json.loads(raw_text)

            title = str(data.get("title", "")).strip()
            subtitle = str(data.get("subtitle", "")).strip()
            footer = str(data.get("footer", "")).strip()

            if not title or not subtitle or not footer:
                return self._fallback(theme)

            return ElderCardText(title=title, subtitle=subtitle, footer=footer)

        except Exception as e:
            print(f"[LLMService] Gemini error: {e}")
            return self._fallback(theme)
