import base64
import json
import os
from html import escape

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

MODEL_NAME = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DIET_OPTIONS = ["No preference", "Vegetarian", "Vegan", "Pescatarian", "Gluten-free", "Dairy-free"]

st.set_page_config(
	page_title="Pantry | Recipe finder",
	page_icon="P",
	layout="wide",
	initial_sidebar_state="expanded",
)

st.markdown(
	"""
	<style>
	@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
	:root { --ink: #24332d; --leaf: #315c46; --tomato: #b94733; --paper: #f7f6f0; --line: #d9ded3; }
	.stApp { background: var(--paper); color: var(--ink); font-family: 'DM Sans', sans-serif; }
	[data-testid="stSidebar"] { background: #e9eee4; border-right: 1px solid var(--line); }
	[data-testid="stSidebar"] p,
	[data-testid="stSidebar"] label,
	[data-testid="stSidebar"] span,
	[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: var(--ink) !important; }
	h1, h2, h3 { color: var(--ink); font-family: 'Playfair Display', Georgia, serif !important; }
	h1 { font-size: 3rem !important; line-height: 1.05 !important; }
	.eyebrow { color: var(--tomato) !important; font-size: .76rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
	.intro { color: #5e6c62; font-size: 1.05rem; max-width: 680px; }
	div.stButton > button { background: #ffffff; border: 1px solid var(--leaf); border-radius: 5px; color: var(--ink) !important; }
	div.stButton > button:hover { background: #e9eee4; border-color: var(--leaf); color: var(--ink) !important; }
	div.stButton > button[kind="primary"] { background: var(--leaf); border: 1px solid var(--leaf); color: #ffffff !important; }
	div.stButton > button[kind="primary"]:hover { background: #244a37; border-color: #244a37; color: #ffffff !important; }
	[data-testid="stFileUploader"] button { background: #ffffff !important; border: 1px solid var(--line) !important; color: var(--ink) !important; }
	[data-testid="stFileUploader"] button span { color: var(--ink) !important; }
	.recipe-meta { color: #647267; font-size: .9rem; padding-bottom: .4rem; border-bottom: 1px solid var(--line); }
	.ingredient-pill { display: inline-block; border: 1px solid var(--line); background: white; border-radius: 3px; padding: .25rem .55rem; margin: .15rem .25rem .15rem 0; color: var(--ink); }
	</style>
	""",
	unsafe_allow_html=True,
)


def get_client(api_key: str) -> OpenAI:
	return OpenAI(
		base_url=OPENROUTER_BASE_URL,
		api_key=api_key,
		default_headers={"X-OpenRouter-Title": "Pantry Recipe Finder"},
	)


def parse_json_object(response_text: str) -> dict:
	decoder = json.JSONDecoder()
	for index, character in enumerate(response_text):
		if character == "{":
			try:
				result, _ = decoder.raw_decode(response_text[index:])
			except json.JSONDecodeError:
				continue
			if isinstance(result, dict):
				return result
	raise ValueError(
		"The model did not return a valid JSON object. Try again or choose a different vision-capable model."
	)


def request_json(client: OpenAI, system_instruction: str, content: str | list[dict]) -> dict:
	response = client.chat.completions.create(
		model=MODEL_NAME,
		messages=[
			{"role": "system", "content": system_instruction},
			{"role": "user", "content": content},
		],
		temperature=0.7,
	)
	response_text = response.choices[0].message.content
	if not isinstance(response_text, str) or not response_text.strip():
		raise ValueError("The model returned an empty response. Please try again.")
	return parse_json_object(response_text)


def add_ingredients(items: list[str]) -> list[str]:
	current = st.session_state.ingredients
	known = {item.casefold() for item in current}
	added = []
	for item in items:
		cleaned = item.strip().strip(".,;: ")
		if cleaned and cleaned.casefold() not in known:
			current.append(cleaned)
			known.add(cleaned.casefold())
			added.append(cleaned)
	return added


def add_manual_ingredients() -> None:
	typed = st.session_state.get("ingredient_input", "")
	add_ingredients(typed.split(","))
	st.session_state.ingredient_input = ""


def identify_and_add(api_key: str, image_bytes: bytes, image_type: str) -> list[str]:
	encoded_image = base64.b64encode(image_bytes).decode("ascii")
	result = request_json(
		get_client(api_key),
		(
			"Identify food ingredients that are clearly visible in the image. "
			"Do not guess hidden items, brands, or quantities. Return JSON only, "
			'with this shape: {"ingredients": ["ingredient name"]}. Do not use markdown. '
			"Use short, common ingredient names."
		),
		[
			{"type": "text", "text": "Which food ingredients are clearly visible?"},
			{
				"type": "image_url",
				"image_url": {"url": f"data:{image_type};base64,{encoded_image}"},
			},
		],
	)
	found = result.get("ingredients", [])
	if not isinstance(found, list):
		raise ValueError("Ingredient recognition returned an unexpected response.")
	return add_ingredients([item for item in found if isinstance(item, str)])


def recommend_recipes(
	api_key: str,
	ingredients: list[str],
	dietary_preference: str,
	max_minutes: int,
	recipe_count: int,
) -> list[dict]:
	result = request_json(
		get_client(api_key),
		(
			"You are a practical recipe assistant. Suggest recipes that use the supplied ingredients. "
			"Do not claim an ingredient is available unless it is listed. You may include a short, "
			"clearly labeled list of common pantry staples the user may need. Respect dietary "
			"requirements and the time limit. Return JSON only, with this shape: "
			'{"recipes": [{"title": "", "description": "", "time_minutes": 30, '
			'"servings": 2, "ingredients": ["..."], "steps": ["..."], '
			'"pantry_staples": ["..."], "uses_from_list": ["..."]}]}. '
			"Do not include markdown or text outside the JSON object."
		),
		(
			f"Available ingredients: {', '.join(ingredients)}. "
			f"Dietary preference: {dietary_preference}. "
			f"Maximum cooking time: {max_minutes} minutes. "
			f"Suggest {recipe_count} distinct recipes."
		),
	)
	recipes = result.get("recipes", [])
	if not isinstance(recipes, list):
		raise ValueError("Recipe generation returned an unexpected response.")
	return [recipe for recipe in recipes if isinstance(recipe, dict)]


def safe_text(value: object, fallback: str = "") -> str:
	return escape(str(value)) if value is not None else fallback


if "ingredients" not in st.session_state:
	st.session_state.ingredients = []
if "recipes" not in st.session_state:
	st.session_state.recipes = []

api_key = os.getenv("OPENROUTER_API_KEY", "")
if not api_key:
	try:
		api_key = st.secrets["OPENROUTER_API_KEY"]
	except (KeyError, StreamlitSecretNotFoundError):
		api_key = ""

with st.sidebar:
	st.markdown('<p class="eyebrow">Your kitchen, reimagined</p>', unsafe_allow_html=True)
	st.subheader("Preferences")
	dietary_preference = st.selectbox("Diet", DIET_OPTIONS)
	max_minutes = st.slider("Maximum cooking time", min_value=15, max_value=120, value=45, step=5)
	recipe_count = st.slider("Recipes to suggest", min_value=1, max_value=5, value=3)
	st.caption(f"Model: {MODEL_NAME}")

st.markdown('<p class="eyebrow">Make something good</p>', unsafe_allow_html=True)
st.title("What’s in your kitchen?")
st.markdown(
	'<p class="intro">Add what you have on hand. We’ll turn your ingredients into recipes worth making.</p>',
	unsafe_allow_html=True,
)

if not api_key:
	st.warning("OpenRouter is not configured. Add OPENROUTER_API_KEY to your local .env file and restart the app.")

left_column, right_column = st.columns([1.05, 0.95], gap="large")

with left_column:
	st.subheader("1. Build your ingredient list")
	st.text_input(
		"Ingredients",
		key="ingredient_input",
		placeholder="e.g. chickpeas, spinach, lemon",
		label_visibility="collapsed",
	)
	st.button("Add ingredients", on_click=add_manual_ingredients)

	st.markdown("**Add from a photo**")
	uploaded_image = st.file_uploader(
		"Choose a photo of ingredients",
		type=["jpg", "jpeg", "png", "webp"],
		label_visibility="collapsed",
	)
	if uploaded_image:
		st.image(uploaded_image, caption="Photo ready for ingredient recognition", width=240)
		if st.button("Identify and add ingredients", disabled=not api_key, key="identify_photo"):
			try:
				with st.spinner("Looking for visible ingredients..."):
					added = identify_and_add(api_key, uploaded_image.getvalue(), uploaded_image.type)
				if added:
					st.success(f"Added: {', '.join(added)}")
				else:
					st.info("No new ingredients were found in the photo.")
			except Exception as error:
				st.error(f"Could not identify ingredients: {error}")

	st.markdown("**Your ingredients**")
	if st.session_state.ingredients:
		for index, ingredient in enumerate(st.session_state.ingredients):
			item_column, remove_column = st.columns([5, 1], vertical_alignment="center")
			item_column.markdown(
				f'<span class="ingredient-pill">{safe_text(ingredient)}</span>',
				unsafe_allow_html=True,
			)
			if remove_column.button("Remove", key=f"remove_{index}", help=f"Remove {ingredient}"):
				st.session_state.ingredients.pop(index)
				st.rerun()
		if st.button("Clear list", key="clear_ingredients"):
			st.session_state.ingredients.clear()
			st.session_state.recipes = []
			st.rerun()
	else:
		st.caption("Your list is empty. Add ingredients above to get started.")

with right_column:
	st.subheader("2. Find your next meal")
	st.write("Recipes are tailored to your ingredient list and preferences.")
	if st.button(
		"Recommend recipes",
		type="primary",
		disabled=not api_key or not st.session_state.ingredients,
		use_container_width=True,
	):
		try:
			with st.spinner("Finding recipes for your kitchen..."):
				st.session_state.recipes = recommend_recipes(
					api_key,
					st.session_state.ingredients.copy(),
					dietary_preference,
					max_minutes,
					recipe_count,
				)
		except Exception as error:
			st.error(f"Could not generate recipes: {error}")

	if st.session_state.recipes:
		st.markdown("---")
		for recipe in st.session_state.recipes:
			with st.container(border=True):
				st.markdown(f"### {safe_text(recipe.get('title'), 'Recipe idea')}")
				description = safe_text(recipe.get("description"))
				if description:
					st.write(description)
				minutes = safe_text(recipe.get("time_minutes", "?"))
				servings = safe_text(recipe.get("servings", "?"))
				st.markdown(
					f'<p class="recipe-meta">{minutes} min &nbsp; | &nbsp; Serves {servings}</p>',
					unsafe_allow_html=True,
				)
				recipe_ingredients = recipe.get("ingredients", [])
				if isinstance(recipe_ingredients, list) and recipe_ingredients:
					st.markdown("**Ingredients**")
					st.markdown("\n".join(f"- {safe_text(item)}" for item in recipe_ingredients))
				steps = recipe.get("steps", [])
				if isinstance(steps, list) and steps:
					st.markdown("**Method**")
					st.markdown("\n".join(f"{index}. {safe_text(step)}" for index, step in enumerate(steps, 1)))
				pantry_staples = recipe.get("pantry_staples", [])
				if isinstance(pantry_staples, list) and pantry_staples:
					staples = ", ".join(safe_text(item) for item in pantry_staples)
					st.caption(f"Pantry staples to check: {staples}")
	elif not st.session_state.ingredients:
		st.caption("Your recipe suggestions will appear here.")
