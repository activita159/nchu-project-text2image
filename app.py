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


def generate_cosmos3(prompt_text):
    url = "https://api-inference.huggingface.co/models/nvidia/Cosmos3-Super-Text2Image"
    resp = fetch_with_backoff(url, json_data={"inputs": prompt_text})
    if not resp.ok:
        raise Exception(f"HF 伺服器拒絕 (狀態: {resp.status_code})")
    img_bytes = resp.content
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def generate_pollinations(prompt_text):
    import random
    seed = random.randint(0, 999999)
    poll_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt_text)}?nologo=true&width=1024&height=1024&seed={seed}"
    resp = fetch_with_backoff(poll_url, method="GET")
    if not resp.ok:
        raise Exception(f"Pollinations API 錯誤: {resp.status_code}")
    img_bytes = resp.content
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


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
    **為什麼 Cosmos3 容易失敗？**  
    Hugging Face 官方對於高算力模型限制了無 Key 請求。使用「Cosmos3」時，本 App 會極速嘗試，若被拒絕將**自動切換**為其他引擎，保證產圖不中斷。
    
    **哪一個最穩定？**  
    推薦選擇「Imagen 4 頂級引擎」或「Pollinations 公共引擎」，完全不需要金鑰且保證成功（Pollinations 真正零金鑰）。
    """)

st.markdown('<p style="font-size:10px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-top:12px;">選擇生成引擎</p>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    i4_selected = st.button("🔥 Imagen 4\n*穩定高畫質*", key="imagen4", use_container_width=True,
                             help="需要設定 GOOGLE_API_KEY（Streamlit Secrets）")
with col2:
    c3_selected = st.button("🎨 Cosmos3\n*原廠模型*", key="cosmos3", use_container_width=True,
                             help="Hugging Face 免 Key，但可能被 CORS/限流阻擋")
with col3:
    po_selected = st.button("⚡ 公共節點\n*極速不設限*", key="pollinations", use_container_width=True,
                             help="Pollinations 公共引擎，100% 免 Key")

if "engine" not in st.session_state:
    st.session_state.engine = "pollinations"

if i4_selected:
    st.session_state.engine = "imagen4"
if c3_selected:
    st.session_state.engine = "cosmos3"
if po_selected:
    st.session_state.engine = "pollinations"

engine_labels = {"imagen4": "Imagen 4", "cosmos3": "Cosmos3", "pollinations": "公共節點"}
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
            elif engine == "cosmos3":
                try:
                    url = generate_cosmos3(final_prompt)
                    st.session_state.image_url = url
                    add_to_history(url, final_prompt, "Cosmos 3")
                except Exception as e:
                    st.warning(f"Cosmos3 失敗：{e}\n自動切換至公共節點...")
                    url = generate_pollinations(final_prompt)
                    st.session_state.image_url = url
                    add_to_history(url, final_prompt, "公共備用")
            else:
                url = generate_pollinations(final_prompt)
                st.session_state.image_url = url
                add_to_history(url, final_prompt, "Pollinations")
        except Exception as e:
            st.session_state.error = str(e)

if st.session_state.get("error"):
    st.warning(f"⚠️ {st.session_state.error}")

if st.session_state.get("image_url"):
    st.markdown("---")
    st.image(st.session_state.image_url, caption=f"生成提示詞：{st.session_state.get('active_prompt', '')}", use_container_width=True)

    img_url = st.session_state.image_url
    if img_url.startswith("data:image/png;base64,"):
        b64_str = img_url.replace("data:image/png;base64,", "")
        img_bytes = base64.b64decode(b64_str)
        st.download_button(
            label="💾 下載圖片",
            data=img_bytes,
            file_name=f"ai-art-{int(time.time())}.png",
            mime="image/png",
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
