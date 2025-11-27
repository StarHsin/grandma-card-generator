from fastapi import FastAPI
import base64
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import GenerateCardRequest, GenerateCardResponse

app = FastAPI()

# 簡單開 CORS 給前端 localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/generate-card", response_model=GenerateCardResponse)
def generate_card(req: GenerateCardRequest):
    # TODO 這裡先用固定圖片替代
    img_path = Path(__file__).parent / "assets" / "sample.png"
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    image_base64 = base64.b64encode(img_bytes).decode("utf-8")

    text = req.custom_text or "早安～祝你今天心情愉快，平安健康！"

    return GenerateCardResponse(
        text=text,
        background_prompt_used="demo fixed image",
        image_mime="image/png",
        image_base64=image_base64,
    )
