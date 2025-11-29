from pydantic import BaseModel
from typing import Optional


class GenerateCardRequest(BaseModel):
    theme: str
    subtype: Optional[str] = None
    custom_text: Optional[str] = None
    background_mode: str = "auto"
    background_prompt: Optional[str] = None
    seed: Optional[int] = None
    width: int = 768
    height: int = 1024


class GenerateCardResponse(BaseModel):
    text: str
    background_prompt_used: str
    image_mime: str
    image_base64: str
