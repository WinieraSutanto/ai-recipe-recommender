# Pantry Recipe Finder

A small Streamlit app that recommends recipes from ingredients you enter or identify in a photo. It uses OpenRouter's OpenAI-compatible API and defaults to its free-model router for recipe generation and photo recognition.

## Run locally

1. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Create an API key in [OpenRouter](https://openrouter.ai/keys). Copy `.env.example` to `.env` and add your key as `OPENROUTER_API_KEY`. The key is read from local configuration and is not entered in the app interface.

4. Start the app:

   ```powershell
   streamlit run app.py
   ```

## Deploy on Streamlit Community Cloud

1. Push the project to a GitHub repository. The `.gitignore` excludes your local `.env` and `.streamlit/secrets.toml`; commit `.env.example` only, which contains a placeholder rather than a real key.
2. Create the app in [Streamlit Community Cloud](https://share.streamlit.io/) and select the repository, branch, and `app.py` entry point.
3. In the app's **Settings > Secrets**, add the key in TOML format:

   ```toml
   OPENROUTER_API_KEY = "your_real_openrouter_key"
   OPENROUTER_MODEL = "openrouter/free"
   ```

4. Save the settings and deploy. The app reads the key from Streamlit secrets in the cloud and from `.env` locally.

Never paste a real key into source code, README files, or GitHub. If a key was ever committed or pushed, revoke it in OpenRouter and create a replacement; deleting it in a later commit does not remove it from Git history.

## Features

- Add a comma-separated list of ingredients.
- Upload a JPG, PNG, or WebP photo to identify visible ingredients and add them to the list.
- Set a dietary preference and cooking-time limit.
- Generate recipes with ingredients, steps, servings, and pantry staples to check.

The image recognition model can make mistakes, so review the ingredient list before generating recipes. Free model availability, rate limits, and vision support are controlled by OpenRouter and may change. Keep `.env` private and do not commit API keys.

The default model, `openrouter/free`, routes requests to an available free model. Free-model availability, limits, and vision support can change. If image recognition fails, choose a free vision-capable model in the OpenRouter model catalog and set its model ID as `OPENROUTER_MODEL` in `.env`. You can also set `OPENROUTER_MODEL` to another model ID supported by your account.
