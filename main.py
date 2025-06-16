from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
import re
import difflib

app = FastAPI()

# Enable CORS for all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data.json (make sure it's in the same folder)
DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

recipe_categories = ["pooja_rituals", "satvik_recipes", "kashmiri_dishes", "general_recipes"]

# Prepare recipe keys and regex patterns for matching
recipe_keywords = []
recipe_key_strings = []

for category in recipe_categories:
    for key in data["recipes"].get(category, {}):
        # Create regex to match key with optional spaces instead of underscores
        pattern = re.compile(
            r"\b" + r".*".join(re.escape(word) for word in key.split("_")) + r"\b",
            re.IGNORECASE,
        )
        recipe_keywords.append((key, pattern))
        recipe_key_strings.append(key)

# Relation and conversation keywords from data
relation_keywords = list(data.get("relation_responses", {}).keys()) if "relation_responses" in data else []
conversation_keywords = list(data.get("conversation_responses", {}).keys()) if "conversation_responses" in data else []

# Alias map for recipes — maps common alternative names and typos to actual keys
aliases = {
    # Karwa Chauth & Rituals
    "karwa chauth": "karwa_chauth",
    "karwa chouth": "karwa_chauth",
    "karwachauth": "karwa_chauth",

    "gowardhan pooja": "gowardhan_pooja",
    "govardhan pooja": "gowardhan_pooja",

    # Satvik Recipes - Pumpkin / Kaddu
    "kaddu": "pumpkin_recipe",
    "pumpkin": "pumpkin_recipe",
    "kaddu recipe": "pumpkin_recipe",
    "pumpkin recipe": "pumpkin_recipe",

    # Bittergourd / Karela
    "karela": "bittergourd_recipe",
    "bittergourd": "bittergourd_recipe",
    "bitter gourd": "bittergourd_recipe",
    "karela recipe": "bittergourd_recipe",
    "bittergourd recipe": "bittergourd_recipe",

    # Buttergourd / Lauki - (You don't have this in JSON but you can add)
    "buttergourd": "lauki_recipe",  # make sure "lauki_recipe" key exists if you add
    "lauki": "lauki_recipe",

    # Kashmiri dishes
    "dum aloo": "kashmiri_dum_aloo",
    "duma aloo": "kashmiri_dum_aloo",
    "dum aaloo": "kashmiri_dum_aloo",
    "kashmiri dum aloo": "kashmiri_dum_aloo",

    "urad dal poori": "urad_dal_poori",
    "urd dal poori": "urad_dal_poori",
    "urad dal puri": "urad_dal_poori",
    "udad dal poori": "urad_dal_poori",

    # Haak (Khaak)
    "haak": "haak",      # If you add haak recipe key
    "khaak": "haak",     # common misspellings

    # You can add more aliases below for future recipes or synonyms
}

def find_recipe_by_key(key: str):
    for category in recipe_categories:
        if key in data["recipes"].get(category, {}):
            return data["recipes"][category][key]
    return None

def find_relation_response(keyword: str):
    return data.get("relation_responses", {}).get(keyword)

def find_conversation_response(keyword: str):
    return data.get("conversation_responses", {}).get(keyword)

class ChatRequest(BaseModel):
    message: str
    language: Optional[str] = "English"

@app.post("/api/chatbot/message")
async def chatbot_response(chat_request: ChatRequest):
    user_msg_raw = chat_request.message.strip()
    user_msg = user_msg_raw.lower()
    lang = chat_request.language if chat_request.language in ["English", "Hindi"] else "English"

    # Greetings shortcut
    if user_msg in ["hi", "hello", "hey", "namaste", "नमस्ते"]:
        return {"response": "Hello! Ask me any family recipe or pooja ritual. 😊"}

    # Check relations responses
    for rel_key in relation_keywords:
        if re.search(r"\b" + re.escape(rel_key) + r"\b", user_msg):
            res = find_relation_response(rel_key)
            if res:
                return {"response": res.get(lang, res.get("English"))}

    # Check conversation responses
    for conv_key in conversation_keywords:
        if re.search(r"\b" + re.escape(conv_key) + r"\b", user_msg):
            res = find_conversation_response(conv_key)
            if res:
                return {"response": res.get(lang, res.get("English"))}

    # Normalize user message to handle spaces, punctuation for alias matching
    normalized_msg = re.sub(r"\s+", " ", user_msg).strip()

    # Check alias map exact match
    if normalized_msg in aliases:
        key = aliases[normalized_msg]
        recipe = find_recipe_by_key(key)
        if recipe:
            return format_recipe_response(recipe, key, lang)

    # Check regex matches for recipes
    for key, pattern in recipe_keywords:
        if pattern.search(user_msg):
            recipe = find_recipe_by_key(key)
            if recipe:
                return format_recipe_response(recipe, key, lang)

    # Fuzzy match fallback for minor typos
    fuzzy_key = normalized_msg.replace(" ", "_")
    close_matches = difflib.get_close_matches(fuzzy_key, recipe_key_strings, n=1, cutoff=0.6)
    if close_matches:
        key = close_matches[0]
        recipe = find_recipe_by_key(key)
        if recipe:
            return format_recipe_response(recipe, key, lang)

    # Final fallback response
    fallback_msg = {
        "English": "Sorry, I couldn't find anything related. Can you try asking differently?",
        "Hindi": "माफ़ कीजिए, मुझे इस बारे में जानकारी नहीं मिली। कृपया कुछ और पूछें।",
    }
    return {"response": fallback_msg[lang]}

def format_recipe_response(recipe: dict, key: str, lang: str):
    if not recipe:
        return {"response": "Recipe not found."}

    title = recipe.get("title", {}).get(lang) or recipe.get("title", {}).get("English", "Recipe")
    ingredients = recipe.get("ingredients", {}).get(lang, [])
    method = recipe.get("method", {}).get(lang, [])
    details = recipe.get("details", {}).get(lang, [])
    tip = recipe.get("tip", {}).get(lang, "")

    response_parts = [f"**{title}**"]

    if ingredients:
        response_parts.append("Ingredients:\n" + "\n".join(f"- {item}" for item in ingredients))

    if method:
        response_parts.append("Method:\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(method)))

    if details:
        response_parts.append("Details:\n" + "\n".join(details))

    if tip:
        response_parts.append("Tip:\n" + tip)

    response_text = "\n\n".join(response_parts).strip()
    return {"response": response_text}
