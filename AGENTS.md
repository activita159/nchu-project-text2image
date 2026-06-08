# AGENTS.md

## Project

Single-file **Streamlit** app (`app.py`) for AI image generation via 3 engines: Pollinations.ai, Hugging Face Inference API, and Google Imagen 4.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Secrets

- Local dev: `.streamlit/secrets.toml` (values are placeholders — real keys live in Streamlit Cloud).
- `GOOGLE_API_KEY` is optional; the app works without it.
- Pollinations.ai API key is optional but recommended (enter in UI, not secrets).

## Architecture

- **`app.py`** — the entire application (UI + backend logic in one file). All generation functions are defined inline.
- **`cosmos3_ai.tsx`** — orphaned React/TSX alternative. No `package.json`, no build config, not part of the active project. Ignore it.

## No test/dev infrastructure

There is no test suite, linter, type-checker, or CI. There is nothing to run beyond `streamlit run app.py`.
