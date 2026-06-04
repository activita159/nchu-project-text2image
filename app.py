import streamlit as st
import requests
import json
import time
import os

SPACE_URL = "https://multimodalart-cosmos3-nano.hf.space"

st.set_page_config(
    page_title="Cosmos3 Text2Image",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp {
        background: #0a0a1a;
    }
    .stApp h1 {
        background: linear-gradient(135deg, #6c5ce7, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 1.8rem !important;
        text-align: center;
        padding-bottom: 0;
    }
    .stApp .caption {
        color: #a0a0bb;
        text-align: center;
        font-size: 0.8rem;
    }
    div[data-testid="stVerticalBlock"] > div:has(> div.element-container > div.stTextArea) {
        position: relative;
    }
    .stTextArea textarea {
        background: #141428 !important;
        border: 2px solid #1e1e3a !important;
        border-radius: 16px !important;
        color: #e8e8f0 !important;
        font-size: 15px !important;
        padding: 14px 48px 14px 16px !important;
        min-height: 56px;
        resize: none;
    }
    .stTextArea textarea:focus {
        border-color: #6c5ce7 !important;
    }
    .stTextArea textarea::placeholder {
        color: #a0a0bb !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #6c5ce7, #a855f7) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 50% !important;
        width: 36px !important;
        height: 36px !important;
        padding: 0 !important;
        font-size: 18px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        position: absolute;
        right: 8px;
        bottom: 8px;
        cursor: pointer;
        z-index: 10;
    }
    .stButton > button:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }
    .stButton > button > div {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    div.stDownloadButton > button {
        flex: 1;
        padding: 10px;
        border: none;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        background: linear-gradient(135deg, #6c5ce7, #a855f7) !important;
        color: #fff !important;
        width: 100%;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 6px;
    }
    div.stColumns > div:has(> div.stButton > button) {
        padding: 0 !important;
    }
    .chip-btn > button {
        background: #141428 !important;
        border: 1px solid #1e1e3a !important;
        border-radius: 14px !important;
        color: #a0a0bb !important;
        font-size: 11px !important;
        padding: 5px 10px !important;
        white-space: nowrap !important;
        width: auto !important;
        height: auto !important;
        position: static !important;
        cursor: pointer;
        transition: all 0.15s;
    }
    .chip-btn > button:active {
        background: #6c5ce7 !important;
        color: #fff !important;
        border-color: #6c5ce7 !important;
    }
    .history-btn > button {
        background: #141428 !important;
        border: 1px solid #1e1e3a !important;
        border-radius: 20px !important;
        color: #a0a0bb !important;
        font-size: 11px !important;
        padding: 6px 12px !important;
        max-width: 160px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        width: auto !important;
        height: auto !important;
        position: static !important;
        cursor: pointer;
        transition: border-color 0.2s;
    }
    .history-btn > button:hover {
        border-color: #6c5ce7 !important;
    }
    .stExpander {
        background: #141428 !important;
        border: 1px solid #1e1e3a !important;
        border-radius: 16px !important;
        margin-bottom: 12px;
    }
    .stExpander summary {
        color: #a0a0bb !important;
        font-size: 13px !important;
    }
    .stSlider label, .stSelectbox label, .stTextInput label, .stCheckbox label, .stNumberInput label {
        color: #a0a0bb !important;
        font-size: 13px !important;
    }
    .stSlider div[data-testid="stMarkdownContainer"] {
        color: #6c5ce7 !important;
        font-size: 12px !important;
    }
    .stSelectbox div[data-baseweb="select"] {
        background: #1e1e3a !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        color: #e8e8f0 !important;
    }
    .stTextInput input, .stNumberInput input {
        background: #1e1e3a !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        color: #e8e8f0 !important;
    }
    .stImage {
        background: #141428 !important;
        border-radius: 16px !important;
        border: 1px solid #1e1e3a !important;
        overflow: hidden;
    }
    .element-container:has(> div.stStatusWidget) {
        display: none;
    }
    [data-testid="stDecoration"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stToolbar"] { display: none; }
    .stAlert {
        background: #141428 !important;
        border: 1px solid #1e1e3a !important;
        color: #e8e8f0 !important;
        border-radius: 10px !important;
    }
    hr { border-color: #1e1e3a !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center'>Cosmos3 Text2Image</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#a0a0bb;font-size:0.8rem;margin-top:-10px'>nvidia/Cosmos3-Nano (16B) · 免金鑰</p>", unsafe_allow_html=True)

SUGGESTIONS = [
    ("🚀 太空人", "Astronaut in a jungle, cold color palette, muted colors, detailed"),
    ("🌸 日式庭園", "A serene Japanese garden with cherry blossoms, pond, wooden bridge"),
    ("🌃 賽博朋克", "Cyberpunk city street at night, neon lights, rain, cinematic lighting"),
    ("🐱 貓咪", "Cute fluffy cat sleeping on a cloud, dreamy soft pastel colors"),
]

if "history" not in st.session_state:
    st.session_state.history = []
if "generated" not in st.session_state:
    st.session_state.generated = False
if "image_bytes" not in st.session_state:
    st.session_state.image_bytes = None
if "image_url" not in st.session_state:
    st.session_state.image_url = None
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = ""
if "seed_used" not in st.session_state:
    st.session_state.seed_used = 0

with st.container():
    prompt = st.text_area(
        "",
        placeholder="輸入圖片描述，例如：A robot reading a book under a cherry tree at sunset...",
        label_visibility="collapsed",
        key="prompt_input",
    )

    send_col1, send_col2, send_col3 = st.columns([1, 1, 1])
    with send_col2:
        generate_clicked = st.button("↑", use_container_width=True)

st.markdown("<div style='display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px'>", unsafe_allow_html=True)
chip_cols = st.columns(4)
for i, (label, sug_prompt) in enumerate(SUGGESTIONS):
    with chip_cols[i]:
        st.markdown('<div class="chip-btn">', unsafe_allow_html=True)
        if st.button(label, key=f"sug_{i}", use_container_width=True):
            st.session_state.prompt_input = sug_prompt
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

with st.expander("⚙ 進階設定"):
    resolution = st.selectbox(
        "解析度",
        ["360p (640x352, fastest)", "480p (832x480, fast)", "720p (1280x720, slow)"],
        index=0,
        key="resolution",
    )
    col1, col2 = st.columns(2)
    with col1:
        steps = st.slider("推論步數", 15, 50, 15, key="steps")
    with col2:
        guidance = st.slider("引導比例", 1.0, 10.0, 4.0, 0.1, key="guidance")
    negative_prompt = st.text_input("負向提示詞", placeholder="排除的內容...", key="negative_prompt")
    col_seed1, col_seed2 = st.columns([1, 3])
    with col_seed1:
        randomize_seed = st.checkbox("隨機種子", True, key="randomize_seed")
    with col_seed2:
        seed = st.number_input("", 0, 999999, 0, disabled=randomize_seed, label_visibility="collapsed", key="seed")

status_placeholder = st.empty()

if generate_clicked or ("run_generation" in st.session_state and st.session_state.run_generation):
    if "run_generation" in st.session_state:
        del st.session_state.run_generation
        prompt = st.session_state.prompt_to_use

    prompt = prompt.strip()
    if not prompt:
        status_placeholder.error("請輸入提示詞")
    else:
        st.session_state.current_prompt = prompt
        status_placeholder.info("Cosmos3-Nano 生成中...")

        params = {
            "mode": "Image",
            "prompt": prompt,
            "image": None,
            "resolution": resolution,
            "num_frames": 65,
            "steps": steps,
            "guidance": guidance,
            "enable_sound": False,
            "negative_prompt": negative_prompt or "",
            "seed": seed,
            "randomize_seed": randomize_seed,
        }

        try:
            submit_resp = requests.post(
                f"{SPACE_URL}/gradio_api/call/v2/generate",
                json=params,
                timeout=30,
            )
            submit_resp.raise_for_status()
            submit_data = submit_resp.json()

            image_url = None
            seed_val = 0

            if submit_data.get("data") and isinstance(submit_data["data"], list) and len(submit_data["data"]) > 0:
                img_data = submit_data["data"][0]
                if isinstance(img_data, dict):
                    if img_data.get("url"):
                        image_url = img_data["url"]
                    elif img_data.get("path"):
                        image_url = f"{SPACE_URL}/gradio_api/file={img_data['path']}"
                elif isinstance(img_data, str):
                    image_url = img_data
                if len(submit_data["data"]) > 2:
                    seed_val = submit_data["data"][2] or 0
            elif submit_data.get("event_id"):
                event_id = submit_data["event_id"]
                sse_url = f"{SPACE_URL}/gradio_api/call/generate/{event_id}"

                with requests.get(sse_url, stream=True, timeout=600) as sse_resp:
                    sse_resp.raise_for_status()
                    event_type = ""
                    event_data = ""
                    found = False

                    for line in sse_resp.iter_lines(decode_unicode=True):
                        if line is None:
                            continue
                        if line.startswith("event: "):
                            event_type = line[7:].strip()
                        elif line.startswith("data: "):
                            event_data = line[6:]
                        elif line == "" and event_data:
                            try:
                                parsed = json.loads(event_data)
                            except json.JSONDecodeError:
                                parsed = None

                            is_complete = event_type in ("complete", "process_completed")
                            is_error = event_type in ("error", "process_error")

                            if not is_complete and not is_error and parsed:
                                if isinstance(parsed, dict):
                                    if parsed.get("msg") == "process_completed":
                                        is_complete = True
                                    elif parsed.get("msg") == "process_error":
                                        is_error = True

                            if not is_complete and not is_error:
                                if isinstance(parsed, list) and len(parsed) > 0:
                                    first = parsed[0]
                                    if isinstance(first, dict) and (first.get("url") or first.get("path")):
                                        is_complete = True

                            if is_complete:
                                output_data = None
                                if parsed and isinstance(parsed, dict):
                                    if parsed.get("output") and parsed["output"].get("data"):
                                        output_data = parsed["output"]["data"]
                                    elif parsed.get("data"):
                                        output_data = parsed["data"]
                                elif isinstance(parsed, list):
                                    output_data = parsed

                                if output_data and len(output_data) > 0:
                                    img_data = output_data[0]
                                    if isinstance(img_data, dict):
                                        if img_data.get("url"):
                                            image_url = img_data["url"]
                                        elif img_data.get("path"):
                                            image_url = f"{SPACE_URL}/gradio_api/file={img_data['path']}"
                                    elif isinstance(img_data, str):
                                        image_url = img_data
                                    if len(output_data) > 2:
                                        seed_val = output_data[2] or 0
                                found = True
                                break

                            if is_error:
                                error_msg = "生成失敗"
                                if parsed:
                                    error_msg = parsed.get("error") or parsed.get("message") or error_msg
                                if "GPU" in error_msg or "duration" in error_msg:
                                    error_msg = "GPU 資源不足，請改用 360p 解析度後重試"
                                raise Exception(error_msg)

                            if parsed and isinstance(parsed, dict) and parsed.get("msg") == "process_generating":
                                pass

                            event_type = ""
                            event_data = ""

                    if not found:
                        raise Exception("生成結果為空")

            if image_url:
                resp = requests.get(image_url, timeout=60)
                resp.raise_for_status()
                st.session_state.image_bytes = resp.content
                st.session_state.image_url = image_url
                st.session_state.seed_used = seed_val
                st.session_state.generated = True

                if prompt not in st.session_state.history:
                    st.session_state.history.insert(0, prompt)
                    if len(st.session_state.history) > 20:
                        st.session_state.history = st.session_state.history[:20]

                status_placeholder.success(f"生成成功！種子: {seed_val}")
                st.rerun()
            else:
                raise Exception("無法取得圖片 URL")

        except requests.exceptions.Timeout:
            status_placeholder.error("請求逾時，請改用 360p 解析度後重試")
        except requests.exceptions.HTTPError as e:
            status_placeholder.error(f"連線失敗 ({e.response.status_code})")
        except Exception as e:
            status_placeholder.error(str(e))

if st.session_state.generated and st.session_state.image_bytes:
    st.image(st.session_state.image_bytes, use_container_width=True)

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            "📥 下載圖片",
            data=st.session_state.image_bytes,
            file_name=f"cosmos3_{int(time.time())}.png",
            mime="image/png",
            use_container_width=True,
        )
    with col_dl2:
        if st.button("📋 複製提示詞", use_container_width=True):
            st.write(f'<textarea id="copyText" style="position:fixed;left:-9999px">{st.session_state.current_prompt}</textarea><script>navigator.clipboard.writeText(document.getElementById("copyText").value)</script>', unsafe_allow_html=True)
            st.toast("已複製提示詞")

if st.session_state.history:
    st.markdown("---")
    st.markdown("<p style='color:#a0a0bb;font-size:13px;margin-bottom:6px'>📜 歷史記錄</p>", unsafe_allow_html=True)
    hist_cols = st.columns(3)
    for idx, hist_prompt in enumerate(st.session_state.history):
        col_idx = idx % 3
        with hist_cols[col_idx]:
            st.markdown('<div class="history-btn">', unsafe_allow_html=True)
            truncated = (hist_prompt[:28] + "…") if len(hist_prompt) > 30 else hist_prompt
            if st.button(truncated, key=f"hist_{idx}", use_container_width=True, help=hist_prompt):
                st.session_state.prompt_input = hist_prompt
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
