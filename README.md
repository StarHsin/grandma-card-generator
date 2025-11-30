👵👴 AI 長輩圖無限生成器 (AI Elder Card Generator)
「認同請分享 🌹」

<img width="2322" height="1220" alt="螢幕擷取畫面 2025-11-30 182345" src="https://github.com/user-attachments/assets/a4dfed9d-8034-4edd-87e9-d8178386634c" />
<img width="807" height="697" alt="螢幕擷取畫面 2025-11-30 182701" src="https://github.com/user-attachments/assets/595bcbb5-d3cc-4642-bac3-c853016f9c42" />
<img width="808" height="686" alt="螢幕擷取畫面 2025-11-30 182743" src="https://github.com/user-attachments/assets/1e0dae4e-85c8-4c96-b6c1-c0f684dcb7f9" />
<img width="1703" height="1157" alt="image" src="https://github.com/user-attachments/assets/302b0bf8-36e9-4a78-9ba2-7648beda841e" />
<img width="1024" height="1024" alt="長輩圖-節慶：一般 🎊-1764499400992" src="https://github.com/user-attachments/assets/53d0817a-0b50-4803-9664-b90b166774ca" />


結合 SDXL Turbo 極速繪圖、Gemini AI 溫暖文案，以及 動態視覺演算法 的全自動長輩圖生成引擎。

📖 專案簡介 (Introduction)
你是否覺得 Line 群組裡的長輩圖千篇一律？ 這個專案旨在解決「長輩圖枯竭危機」。我們利用現代 AI 技術，將傳統的長輩圖製作過程完全自動化。從背景生成、文案撰寫到排版設計，全部由 AI 即時完成，確保每一張圖都是獨一無二的祝福。

✨ 核心特色 (Key Features)
⚡️ 極速背景生成 (SDXL Turbo)：利用 Latent Consistency Model 技術，只需 1 步運算即可生成高品質風景、花卉背景（需配合生成腳本）。

🧠 靈魂文案注入 (Gemini AI)：

透過 Prompt Engineering 設定「溫暖文案師」角色。

支援多種風格（溫馨、幽默、穩重）隨機切換。

拒絕罐頭回覆，根據節慶與主題（如：早安、健康、新年）生成客製化內容。

🎨 智慧動態排版 (Smart Layout Engine)：

自動偵測留白：演算法計算背景圖片各區域的像素複雜度 (Standard Deviation)，自動將文字安置在最乾淨的區域。

自適應高對比配色：依據背景亮度 (Luminance) 自動調整文字顏色與描邊（亮字配黑邊、暗字配白邊），確保絕對的可讀性。

多樣化構圖：支援經典置中、直書（文青風）、左側區塊、對角線等多種排版。

🖥️ 互動式前端：基於 React + Tailwind CSS + shadcn/ui 打造的現代化操作介面。

🛠️ 技術架構 (Tech Stack)
Backend: Python 3.10+, FastAPI

Frontend: React, Vite, Tailwind CSS

Image Processing: Pillow (PIL)

AI Models:

Text: Google Gemini (via google-genai SDK)

Image: SDXL Turbo (via diffusers)


💡 演算法解析 (Algorithm Deep Dive)
本專案在 graphics_utils.py 中實作了特殊的排版決策邏輯：

複雜度分析：對圖片不同區域（如中央、上下、左側）進行採樣。

標準差計算：region_complexity() 計算該區域的像素標準差。標準差越低代表該區域顏色越單一（如天空、水面）。

最佳解選擇：系統自動選取「最乾淨」的區域來放置文字，避免文字與背景雜物重疊。

直書處理：針對中文特性，支援直式排版，並自動處理中英文混排時的佈局問題。
