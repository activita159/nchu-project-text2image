import streamlit as st
import requests
import time
import io
import base64
from datetime import datetime

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
    .stButton > button { border-radius: 12px !important; font-weight: 600 !important; }
    .engine-btn { border-radius: 14px !important; padding: 14px 8px !important; }
    .preset-btn > button { border-radius: 20px !important; font-size: 11px !important; padding: 6px 14px !important; background-color: #1e293b !important; border: 1px solid #334155 !important; color: #cbd5e1 !important; }
    section[data-testid="stSidebar"] { background-color: #0f172a; }
    div[data-testid="stMarkdownContainer"] { color: #e2e8f0; }
</style>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = []

GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", "")

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


def generate_imagen4(prompt_text):
    if not GOOGLE_API_KEY:
        raise Exception("未設定 GOOGLE_API_KEY，請於 Streamlit Secrets 中設定。")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={GOOGLE_API_KEY}"
    resp = fetch_with_backoff(url, json_data={
        "instances": {"prompt": prompt_text},
        "parameters": {"sampleCount": 1}
    })
    if not resp.ok:
        raise Exception(f"Imagen API 回傳錯誤碼: {resp.status_code}")
    result = resp.json()
    b64 = result.get("predictions", [{}])[0].get("bytesBase64Encoded")
    if not b64:
        raise Exception("未能成功解碼圖片資料。")
    return f"data:image/png;base64,{b64}"


def generate_hf_sd(prompt_text):
    url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
    try:
        resp = fetch_with_backoff(url, json_data={"inputs": prompt_text}, max_retries=2)
        if not resp.ok:
            raise Exception(f"HF SD 伺服器拒絕 (狀態: {resp.status_code})")
        img_bytes = resp.content
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except (requests.ConnectionError, requests.Timeout) as e:
        raise Exception(f"HF SD 無法連線（Streamlit Cloud 網路限制）: {e}")


def generate_stablehorde(prompt_text):
    submit_url = "https://stablehorde.net/api/v2/generate/async"
    headers = {"apikey": "0000000000", "Content-Type": "application/json"}
    payload = {
        "prompt": prompt_text,
        "params": {"width": 1024, "height": 1024, "steps": 30},
        "nsfw": True,
        "censor_nsfw": False,
        "r2": True,
        "shared": True,
    }
    submit_resp = requests.post(submit_url, json=payload, headers=headers, timeout=30)
    if not submit_resp.ok:
        error_detail = submit_resp.text[:300]
        raise Exception(f"Stable Horde 請求失敗 ({submit_resp.status_code}): {error_detail}")
    task_id = submit_resp.json().get("id")
    if not task_id:
        raise Exception("未取得 Stable Horde 任務 ID")

    for attempt in range(36):
        time.sleep(5)
        try:
            check_resp = requests.get(
                f"https://stablehorde.net/api/v2/generate/status/{task_id}",
                headers=headers,
                timeout=30,
            )
            if not check_resp.ok:
                continue
            status = check_resp.json()
            if status.get("done"):
                generations = status.get("generations", [])
                if not generations:
                    raise Exception("Stable Horde 回傳為空")
                img_b64 = generations[0].get("img")
                if not img_b64:
                    raise Exception("Stable Horde 圖片資料為空")
                return f"data:image/webp;base64,{img_b64}"
            if status.get("faulted"):
                fault_msg = status.get("faulted", "未知錯誤")
                raise Exception(f"Stable Horde 任務故障: {fault_msg}")
        except requests.RequestException:
            if attempt > 33:
                raise
    raise Exception("Stable Horde 排隊逾時（3分鐘），請稍後重試")


# --- UI ---

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

with st.expander("💡 常見連線說明", expanded=False):
    st.markdown("""
    **三大免費繪圖引擎比較**
    - **Imagen 4**：Google 頂級模型，畫質最優，需設定 Google API Key。
    - **HF SD 2.1**：Hugging Face 託管的 Stable Diffusion，完全免費、匿名使用。
    - **Stable Horde**：群眾分散式運算網路，免費免金鑰，排隊約 10~60 秒即出圖。
    """)

st.markdown('<p style="font-size:10px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-top:12px;">選擇生成引擎</p>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    i4_selected = st.button("🔥 Imagen 4\n*頂級畫質*", key="imagen4", use_container_width=True,
                             help="需要設定 GOOGLE_API_KEY（Streamlit Secrets）")
with col2:
    hf_selected = st.button("🎨 HF SD 2.1\n*免費快速*", key="hfsd", use_container_width=True,
                             help="Hugging Face 免費 Stable Diffusion 2.1")
with col3:
    sh_selected = st.button("⚡ Stable Horde\n*免費高品質*", key="stablehorde", use_container_width=True,
                             help="分散式運算網路，100% 免費免金鑰")

if "engine" not in st.session_state:
    st.session_state.engine = "stablehorde"

if i4_selected:
    st.session_state.engine = "imagen4"
if hf_selected:
    st.session_state.engine = "hfsd"
if sh_selected:
    st.session_state.engine = "stablehorde"

engine_labels = {"imagen4": "Imagen 4", "hfsd": "HF Stable Diffusion 2.1", "stablehorde": "Stable Horde"}
st.caption(f"目前引擎：**{engine_labels[st.session_state.engine]}**")

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

st.caption("按 Enter 或點擊按鈕直接產生圖片 · 建議使用英文以獲得最佳繪圖效果")

if generate_btn and final_prompt:
    st.session_state.active_prompt = final_prompt
    with st.spinner("🚀 正在生成圖片..."):
        st.session_state.error = None
        st.session_state.image_url = None
        try:
            engine = st.session_state.engine
            if engine == "imagen4":
                url = generate_imagen4(final_prompt)
                st.session_state.image_url = url
                add_to_history(url, final_prompt, "Imagen 4")
            elif engine == "hfsd":
                try:
                    url = generate_hf_sd(final_prompt)
                    st.session_state.image_url = url
                    add_to_history(url, final_prompt, "HF SD 2.1")
                except Exception as e:
                    st.warning(f"HF SD 失敗：{e}\n自動切換至 Stable Horde...")
                    url = generate_stablehorde(final_prompt)
                    st.session_state.image_url = url
                    add_to_history(url, final_prompt, "Stable Horde(備援)")
            else:
                url = generate_stablehorde(final_prompt)
                st.session_state.image_url = url
                add_to_history(url, final_prompt, "Stable Horde")
        except Exception as e:
            st.session_state.error = str(e)

if st.session_state.get("error"):
    st.warning(f"⚠️ {st.session_state.error}")

if st.session_state.get("image_url"):
    st.markdown("---")
    st.image(st.session_state.image_url, caption=f"生成提示詞：{st.session_state.get('active_prompt', '')}", use_container_width=True)

    img_url = st.session_state.image_url
    if img_url.startswith("data:image/"):
        b64_str = img_url.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_str)
        ext = "webp" if "webp" in img_url else "png"
        st.download_button(
            label="💾 下載圖片",
            data=img_bytes,
            file_name=f"ai-art-{int(time.time())}.{ext}",
            mime=f"image/{ext}",
            use_container_width=True,
        )
    else:
        st.markdown(f'<a href="{img_url}" target="_blank"><button style="width:100%;padding:8px;border-radius:10px;background:#2563eb;color:white;border:none;cursor:pointer;font-weight:600;">💾 在新分頁下載</button></a>', unsafe_allow_html=True)

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
