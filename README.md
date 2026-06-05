# Cosmos3 AI Studio

行動版智能 AI 繪圖套件，使用 Streamlit 部署。

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nchu-project-text2image-ufkeepavj87iyjuksuna5w.streamlit.app/)

## 功能

- **Stable Horde**：群眾分散式運算網路，免費註冊後即可使用
- **Imagen 4**：Google 頂級繪圖模型（需 API Key）
- 5 種風格快捷標籤（寫實攝影、概念插畫、賽博朋克、3D 黏土、吉卜力風）
- 歷史記錄（最新 10 張）
- 圖片下載

## 快速開始

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Secrets 設定

在 Streamlit Cloud App Settings → Secrets 中設定：

```toml
STABLEHORDE_API_KEY = "你的-key"   # 必填，至 https://stablehorde.net/register 免費註冊
GOOGLE_API_KEY = "你的-key"        # 選填
```

## 線上 Demo

[https://nchu-project-text2image-ufkeepavj87iyjuksuna5w.streamlit.app/](https://nchu-project-text2image-ufkeepavj87iyjuksuna5w.streamlit.app/)
