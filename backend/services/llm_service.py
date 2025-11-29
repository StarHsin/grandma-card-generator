from dataclasses import dataclass
from typing import Dict


@dataclass
class ElderCardText:
    title: str
    subtitle: str
    footer: str


class LLMService:
    """
    現階段先用硬寫模板，之後再換成真的 LLM 呼叫。
    """

    def __init__(self):
        # 不同主題的預設模板，可以依你的 persona 微調
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
        }

    def generate_text(self, theme: str) -> ElderCardText:
        """
        未來這裡可以改成呼叫 GPT / Gemini：
        - 把 persona 放在 system prompt
        - 把主題 + 風格 + few-shot 當 user prompt
        - 要求模型輸出 JSON（title/subtitle/footer）
        """
        if theme in self.templates:
            return self.templates[theme]

        # 不支援的主題就給一個通用版本
        return ElderCardText(
            title="送上暖暖的祝福",
            subtitle="不管今天忙不忙，都別忘了幫自己留一點喘口氣的時間。",
            footer="把這張充滿祝福的小卡，傳給你在乎的人吧 ❤️",
        )
