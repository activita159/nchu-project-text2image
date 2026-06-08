import sys
import io as _io
import locale
import os
import random
import urllib.parse

if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    locale.getpreferredencoding = lambda do_setlocale=True: 'utf-8'
    try:
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

import streamlit as st
import requests
import time
import io
import base64
from datetime import datetime
from PIL import Image

st.set_page_config(
    page_title="Cosmos3 AI Studio",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp { background-color: #0f172a; }
    .stTextArea textarea { background-color: #1e293b !important; color: #e2e8f0 !important; border-color: #334155 !important; font-size: 14px !important; }
    .stTextArea textarea::placeholder { color: #64748b !important; }
    .stTextInput input { background-color: #1e293b !important; color: #e2e8f0 !important; border-color: #334155 !important; }
    .stTextInput input::placeholder { color: #64748b !important; }
    .stButton > button { border-radius: 12px !important; font-weight: 600 !important; }
    .preset-btn > button { border-radius: 20px !important; font-size: 11px !important; padding: 6px 14px !important; background-color: #1e293b !important; border: 1px solid #334155 !important; color: #cbd5e1 !important; }
    section[data-testid="stSidebar"] { background-color: #0f172a; }
    div[data-testid="stMarkdownContainer"] { color: #e2e8f0; }
    .engine-box { background: linear-gradient(135deg, #1e293b, #0f2040); border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = []

GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", "")

# ── Pollinations 可選模型 ──────────────────────────────────────────────────────
POLLINATIONS_MODELS = [
    ("flux",          "FLUX（預設）",      "最新擴散模型，品質高"),
    ("flux-realism",  "FLUX Realism",      "寫實風格加強版"),
    ("flux-anime",    "FLUX Anime",        "動漫風格"),
    ("flux-3d",       "FLUX 3D",           "3D 渲染風格"),
    ("turbo",         "Turbo",             "速度最快，品質略低"),
]
POLL_MODEL_IDS   = [m[0] for m in POLLINATIONS_MODELS]
POLL_MODEL_NAMES = [f"{m[1]}  —  {m[2]}" for m in POLLINATIONS_MODELS]

# ── Hugging Face 可選模型 ──────────────────────────────────────────────────────
HF_MODELS = [
    ("black-forest-labs/FLUX.1-schnell",          "FLUX.1-schnell",  "最快速，通常 10–20s"),
    ("black-forest-labs/FLUX.1-dev",              "FLUX.1-dev",      "高品質，需較長等待"),
    ("stabilityai/stable-diffusion-xl-base-1.0",  "SDXL 1.0",        "經典穩定擴散 XL"),
    ("runwayml/stable-diffusion-v1-5",            "SD 1.5",          "輕量快速，廣泛支援"),
]
HF_MODEL_IDS   = [m[0] for m in HF_MODELS]
HF_MODEL_NAMES = [f"{m[1]}  —  {m[2]}" for m in HF_MODELS]

STYLE_PRESETS = [
    ("🌟 寫實攝影", ", realistic photography, highly detailed, 8k resolution, professional lighting"),
    ("🎨 概念插畫", ", digital illustration, fantasy concept art, vibrant colors, masterpiece"),
    ("👾 賽博朋克", ", cyberpunk style, neon lights, futuristic city, dark synthwave aesthetics"),
    ("🧸 3D 黏土", ", cute 3D clay style, Pixar animation aesthetic, soft lighting, pastel colors"),
    ("🎌 吉卜力風", ", Studio Ghibli anime style, hand-drawn watercolor, nostalgic, retro"),
]


def clean_prompt(raw: str) -> str:
    return raw.strip().lstrip(",").strip()


def fetch_with_backoff(url, method="POST", json_data=None, max_retries=5, headers=None):
    delay = 1
    for i in range(max_retries):
        try:
            if method == "POST":
                resp = requests.post(url, json=json_data, headers=headers, timeout=30)
            else:
                resp = requests.get(url, timeout=30)
            if resp.ok:
                return resp
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(delay)
                delay *= 2
                continue
            return resp
        except requests.RequestException:
            if i == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    raise Exception("連線逾時，重試失敗。")


def add_to_history(url, prompt_text, engine_name):
    st.session_state.history.insert(0, {
        "id": datetime.now().timestamp(),
        "url": url,
        "prompt": prompt_text,
        "engine": engine_name,
    })
    st.session_state.history = st.session_state.history[:10]


# ── Imagen 4 ──────────────────────────────────────────────────────────────────
def generate_imagen4(prompt_text):
    api_key = GOOGLE_API_KEY.strip() if GOOGLE_API_KEY else ""
    if not api_key:
        raise Exception("未設定 GOOGLE_API_KEY，請於 Streamlit Secrets 中設定。")
    try:
        api_key.encode('ascii')
    except UnicodeEncodeError:
        raise Exception("GOOGLE_API_KEY 包含非英文字元，請確認設定是否正確。")
    if any(x in api_key for x in ["你的", "your-", "YOUR-"]):
        raise Exception("GOOGLE_API_KEY 為預設預留字，請設定真實的金鑰。")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={api_key}"
    resp = fetch_with_backoff(url, json_data={
        "instances": {"prompt": prompt_text},
        "parameters": {"sampleCount": 1}
    })
    if not resp.ok:
        raise Exception(f"Imagen API 回傳錯誤碼: {resp.status_code}")
    b64 = resp.json().get("predictions", [{}])[0].get("bytesBase64Encoded")
    if not b64:
        raise Exception("未能成功解碼圖片資料。")
    return f"data:image/png;base64,{b64}"


# ── Pollinations.ai（免費、無需 Key）─────────────────────────────────────────
def generate_pollinations(prompt_text, model_id: str):
    """
    呼叫 Pollinations.ai 免費圖片生成 API。
    GET https://image.pollinations.ai/prompt/{encoded_prompt}?model=...&width=512&height=512&nologo=true&seed=...
    直接回傳 JPEG 圖片二進位。
    """
    seed = random.randint(1, 999999)
    encoded = urllib.parse.quote(prompt_text)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?model={model_id}&width=512&height=512&nologo=true&seed={seed}"
    )

    progress = st.empty()
    progress.info("⚙️ 正在呼叫 Pollinations.ai，請稍候（通常 10–30 秒）...")

    try:
        resp = requests.get(url, timeout=90)
    except requests.Timeout:
        progress.empty()
        raise Exception("Pollinations.ai 請求逾時（90秒），請稍後重試。")
    except requests.RequestException as e:
        progress.empty()
        raise Exception(f"網路連線錯誤：{e}")

    if not resp.ok:
        progress.empty()
        raise Exception(f"Pollinations.ai 回傳錯誤 ({resp.status_code})，請重試。")

    img_bytes = resp.content
    if len(img_bytes) < 500:
        progress.empty()
        raise Exception("回傳資料過小，可能不是有效圖片，請重試。")

    progress.empty()
    b64 = base64.b64encode(img_bytes).decode()
    return f"data:image/jpeg;base64,{b64}"


# ── Hugging Face Inference API（需使用者自行填入 Token）──────────────────────
def generate_huggingface(prompt_text, hf_token: str, model_id: str):
    token = hf_token.strip() if hf_token else ""
    if not token:
        raise Exception(
            "請在下方欄位填入您的 Hugging Face API Token。\n"
            "尚無 Token？前往 https://huggingface.co/settings/tokens 免費申請（Read 權限即可）。"
        )
    if not token.startswith("hf_"):
        raise Exception("Token 格式錯誤，Hugging Face Token 應以 hf_ 開頭，請重新確認。")

    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "image/jpeg",
    }
    payload = {"inputs": prompt_text}

    progress = st.empty()
    max_retries = 6
    for attempt in range(max_retries):
        progress.info(f"⚙️ 呼叫 Hugging Face API... (第 {attempt + 1}/{max_retries} 次嘗試)")
        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=120)
        except requests.Timeout:
            if attempt < max_retries - 1:
                progress.warning(f"⏳ 請求逾時，重試中... ({attempt + 1}/{max_retries})")
                time.sleep(10)
                continue
            progress.empty()
            raise Exception("Hugging Face API 請求逾時（2分鐘），請稍後重試。")
        except requests.RequestException as e:
            progress.empty()
            raise Exception(
                f"網路連線失敗：{e}\n\n"
                "⚠️ 提示：Streamlit Community Cloud 可能封鎖了 HuggingFace 的連線。\n"
                "建議改用上方的「Pollinations.ai」引擎（免費、無需 Key）。"
            )

        if resp.status_code == 503:
            try:
                estimated = resp.json().get("estimated_time", 20)
            except Exception:
                estimated = 20
            wait = min(int(estimated) + 5, 35)
            progress.info(f"🔄 模型載入中（冷啟動），預計 {estimated:.0f}s，等待 {wait}s 後重試... ({attempt + 1}/{max_retries})")
            time.sleep(wait)
            continue
        if resp.status_code == 401:
            progress.empty()
            raise Exception("Token 驗證失敗（401），請確認 Hugging Face Token 正確且具備 Read 權限。")
        if resp.status_code == 403:
            progress.empty()
            raise Exception(f"存取被拒（403），請先至以下頁面同意使用條款：https://huggingface.co/{model_id}")
        if resp.status_code == 429:
            progress.warning(f"⚠️ 請求頻率過高（429），等待後重試... ({attempt + 1}/{max_retries})")
            time.sleep(15)
            continue
        if not resp.ok:
            try:
                err_detail = resp.json().get("error", resp.text[:300])
            except Exception:
                err_detail = resp.text[:300]
            progress.empty()
            raise Exception(f"Hugging Face API 錯誤 ({resp.status_code}): {err_detail}")

        img_bytes = resp.content
        if len(img_bytes) < 100:
            progress.empty()
            raise Exception("回傳資料過小，可能不是有效圖片，請重試。")

        progress.empty()
        content_type = resp.headers.get("content-type", "image/jpeg")
        ext = "png" if "png" in content_type else ("webp" if "webp" in content_type else "jpeg")
        b64 = base64.b64encode(img_bytes).decode()
        return f"data:image/{ext};base64,{b64}"

    progress.empty()
    raise Exception("Hugging Face 模型多次嘗試後仍未回應，請稍後重試。")


# ── UI ────────────────────────────────────────────────────────────────────────

_, c1, _ = st.columns([1, 3, 1])
with c1:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <div style="background:linear-gradient(135deg,#2563eb,#6366f1);padding:6px;border-radius:10px;display:flex;">
            <span style="font-size:18px;">✨</span>
        </div>
        <div>
            <h1 style="font-size:16px;margin:0;color:#f1f5f9;">Cosmos3 AI Studio</h1>
            <p style="font-size:10px;margin:0;color:#94a3b8;">智能繪圖套件</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with st.expander("💡 連線說明", expanded=False):
    st.markdown("""
    **三個繪圖引擎**
    - **🆓 Pollinations.ai**（預設）：完全免費、無需任何 API Key，使用 FLUX 等模型，直接可用。
    - **🤗 Hugging Face**：需填入自己的 HF Token（免費申請），但 Streamlit Cloud 環境可能受網路限制。
    - **🔥 Imagen 4**：Google 頂級模型，需在 Streamlit Secrets 中設定 `GOOGLE_API_KEY`。
    """)

# ── 引擎選擇 ──────────────────────────────────────────────────────────────────
st.markdown('<p style="font-size:10px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-top:12px;">選擇生成引擎</p>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    poll_selected = st.button("🆓 Pollinations.ai\n*免費無需 Key*", key="poll_engine", use_container_width=True,
                              help="完全免費，支援 FLUX / Turbo 等多種模型，無需任何帳號")
with col2:
    hf_selected = st.button("🤗 Hugging Face\n*需填入 Token*", key="hf_engine", use_container_width=True,
                             help="需填入自己的 HF Token，Streamlit Cloud 可能受網路限制")
with col3:
    i4_selected = st.button("🔥 Imagen 4\n*需 Google Key*", key="imagen4", use_container_width=True,
                             help="需設定 GOOGLE_API_KEY 於 Streamlit Secrets")

if "engine" not in st.session_state:
    st.session_state.engine = "pollinations"

if poll_selected:
    st.session_state.engine = "pollinations"
if hf_selected:
    st.session_state.engine = "huggingface"
if i4_selected:
    st.session_state.engine = "imagen4"

engine_labels = {"pollinations": "Pollinations.ai", "huggingface": "Hugging Face", "imagen4": "Imagen 4"}
st.caption(f"目前引擎：**{engine_labels[st.session_state.engine]}**")

# ── Pollinations 設定 ─────────────────────────────────────────────────────────
if st.session_state.engine == "pollinations":
    selected_poll_name = st.selectbox(
        "Pollinations 模型",
        options=POLL_MODEL_NAMES,
        key="poll_model_name",
        label_visibility="collapsed",
    )
    selected_poll_idx = POLL_MODEL_NAMES.index(selected_poll_name)
    selected_poll_id  = POLL_MODEL_IDS[selected_poll_idx]
    st.caption(f"📌 使用模型：`{selected_poll_id}`　免費 · 無需帳號")
else:
    selected_poll_id = POLL_MODEL_IDS[0]

# ── Hugging Face 設定 ─────────────────────────────────────────────────────────
if st.session_state.engine == "huggingface":
    st.markdown("""
    <div class="engine-box">
        <p style="margin:0 0 6px 0;font-size:11px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:1px;">
            🤗 Hugging Face 設定
        </p>
    </div>
    """, unsafe_allow_html=True)

    hf_col1, hf_col2 = st.columns([3, 2])
    with hf_col1:
        hf_token_input = st.text_input(
            "HF API Token",
            key="hf_token",
            placeholder="hf_xxxxxxxxxxxxxxxxxxxx",
            type="password",
            help="前往 https://huggingface.co/settings/tokens 申請免費 Token（Read 權限即可）",
            label_visibility="collapsed",
        )
    with hf_col2:
        selected_hf_name = st.selectbox(
            "HF 模型",
            options=HF_MODEL_NAMES,
            key="hf_model_name",
            label_visibility="collapsed",
        )
    selected_hf_idx = HF_MODEL_NAMES.index(selected_hf_name)
    selected_hf_id  = HF_MODEL_IDS[selected_hf_idx]
    st.caption(f"📌 模型 ID：`{selected_hf_id}`　　[HuggingFace 頁面](https://huggingface.co/{selected_hf_id})")
    st.warning("⚠️ Streamlit Community Cloud 可能封鎖對外連線，若出現 DNS 錯誤請改用 **Pollinations.ai** 引擎。", icon="⚠️")
else:
    hf_token_input = ""
    selected_hf_id  = HF_MODEL_IDS[0]

# ── 風格快速渲染 ───────────────────────────────────────────────────────────────
st.markdown('<p style="font-size:10px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-top:16px;">風格快速渲染</p>', unsafe_allow_html=True)

preset_cols = st.columns(len(STYLE_PRESETS))
for i, (label, value) in enumerate(STYLE_PRESETS):
    with preset_cols[i]:
        if st.button(label, key=f"preset_{i}"):
            if "prompt" not in st.session_state:
                st.session_state.prompt = ""
            if value not in st.session_state.prompt:
                st.session_state.prompt = (st.session_state.prompt + value).strip()
                st.rerun()

prompt = st.text_area(
    "請輸入英文描述您想像的畫面",
    key="prompt",
    placeholder="A futuristic city skyline at sunset...",
    height=100,
    label_visibility="collapsed",
)

c1, c2, c3 = st.columns([2, 1, 2])
with c2:
    final_prompt = clean_prompt(prompt.strip()) if prompt.strip() else ""
    generate_btn = st.button("✨ 生成圖片", use_container_width=True, type="primary", disabled=not final_prompt)

st.caption("點擊按鈕產生圖片 · 建議使用英文以獲得最佳繪圖效果")

# ── 生成邏輯 ──────────────────────────────────────────────────────────────────
if generate_btn and final_prompt:
    st.session_state.active_prompt = final_prompt
    st.session_state.error = None
    st.session_state.image_url = None
    try:
        engine = st.session_state.engine
        with st.status(f"🚀 使用 {engine_labels.get(engine, engine)} 生成中...", expanded=True) as status:
            st.write(f"提示詞：{final_prompt}")
            if engine == "imagen4":
                st.write("正在呼叫 Imagen 4 API...")
                url = generate_imagen4(final_prompt)
                st.session_state.image_url = url
                add_to_history(url, final_prompt, "Imagen 4")
            elif engine == "huggingface":
                st.write(f"正在呼叫 Hugging Face API（{selected_hf_id}）...")
                url = generate_huggingface(final_prompt, hf_token_input, selected_hf_id)
                st.session_state.image_url = url
                add_to_history(url, final_prompt, f"HF/{HF_MODELS[selected_hf_idx][1]}")
            else:  # pollinations
                st.write(f"正在呼叫 Pollinations.ai（{selected_poll_id}）...")
                url = generate_pollinations(final_prompt, selected_poll_id)
                st.session_state.image_url = url
                add_to_history(url, final_prompt, f"Pollinations/{POLLINATIONS_MODELS[selected_poll_idx][1]}")
            status.update(label="✅ 生成完成！", state="complete")
    except Exception as e:
        st.session_state.error = str(e)
        print(f"[ERROR] {e}", flush=True)
        import traceback
        st.exception(e)

if st.session_state.get("error"):
    st.error(f"⚠️ {st.session_state.error}")

# ── 圖片顯示 ──────────────────────────────────────────────────────────────────
if st.session_state.get("image_url"):
    st.markdown("---")
    img_url = st.session_state.image_url
    st.caption(f"生成提示詞：{st.session_state.get('active_prompt', '')}")
    if img_url.startswith("data:image/"):
        b64_str = img_url.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_str)
        ext = "webp" if "webp" in img_url else ("png" if "png" in img_url else "jpeg")
        try:
            pil_img = Image.open(io.BytesIO(img_bytes))
            st.image(pil_img, use_container_width=True)
        except Exception as img_err:
            st.warning(f"圖片解碼失敗：{img_err}")
            st.markdown(
                f'<img src="{img_url}" style="max-width:100%;border-radius:12px;" />',
                unsafe_allow_html=True,
            )
        st.download_button(
            label="💾 下載圖片",
            data=img_bytes,
            file_name=f"ai-art-{int(time.time())}.{ext}",
            mime=f"image/{ext}",
            use_container_width=True,
        )
    else:
        st.image(img_url, use_container_width=True)
        st.markdown(f'<a href="{img_url}" target="_blank"><button style="width:100%;padding:8px;border-radius:10px;background:#2563eb;color:white;border:none;cursor:pointer;font-weight:600;">💾 在新分頁下載</button></a>', unsafe_allow_html=True)

# ── 歷史記錄 ──────────────────────────────────────────────────────────────────
if st.session_state.history:
    st.markdown("---")
    st.markdown('<p style="font-size:10px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:1px;">🕐 最近繪製記錄</p>', unsafe_allow_html=True)

    hist_cols = st.columns(5)
    for i, item in enumerate(st.session_state.history):
        with hist_cols[i % 5]:
            st.image(item["url"], use_container_width=True)
            st.caption(f"{item['engine']}")
            if st.button("載入", key=f"load_{item['id']}"):
                st.session_state.prompt = item["prompt"]
                st.session_state.image_url = item["url"]
                st.rerun()

    if st.button("🗑️ 清除記錄", key="clear_history"):
        st.session_state.history = []
        st.rerun()
