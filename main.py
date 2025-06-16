from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
import re
import difflib

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data.json
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

recipe_categories = ['pooja_rituals', 'satvik_recipes', 'kashmiri_dishes', 'general_recipes']

# Aliases dictionary: common names, typos, and simpler user inputs mapped to keys in data.json
aliases = {
    # Pooja rituals
    "karwa chauth": "karwa_chauth",
    "karwa chauth pooja": "karwa_chauth",
    "karwachauth": "karwa_chauth",
    "karva chauth": "karwa_chauth",
    "karwachauth pooja": "karwa_chauth",

    "gowardhan pooja": "gowardhan_pooja",
    "govardhan pooja": "gowardhan_pooja",

    # Satvik recipes
    "kaddu": "pumpkin_recipe",
    "pumpkin": "pumpkin_recipe",
    "pumpkin recipe": "pumpkin_recipe",
    "kaddu recipe": "pumpkin_recipe",

    "karela": "bittergourd_recipe",
    "bittergourd": "bittergourd_recipe",
    "bitter gourd": "bittergourd_recipe",
    "karela recipe": "bittergourd_recipe",
    "bittergourd recipe": "bittergourd_recipe",
    "kaarela": "bittergourd_recipe",

    # Kashmiri dishes
    "dum aloo": "kashmiri_dum_aloo",
    "duma aloo": "kashmiri_dum_aloo",
    "kashmiri dum aloo": "kashmiri_dum_aloo",
    "kashmiri dumalu": "kashmiri_dum_aloo",

    "urad dal poori": "urad_dal_poori",
    "udad dal poori": "urad_dal_poori",
    "urad dal puri": "urad_dal_poori",
    "udad dal puri": "urad_dal_poori",
    "poori": "urad_dal_poori",
    "puri": "urad_dal_poori",
    "urad": "urad_dal_poori",

    # Haak aliases (Kashmiri green leafy vegetable dish)
    "haak": "haak_recipe",
    "haak recipe": "haak_recipe",
    "hak": "haak_recipe",
    "kashmiri haak": "haak_recipe",
    "kashmiri hak": "haak_recipe",

    # Add more aliases here as you add more recipes or common variations
}

# Build regex patterns for all recipes keys to match user messages
recipe_keywords = []
recipe_key_strings = []

for category in recipe_categories:
    for key in data['recipes'].get(category, {}):
        # regex pattern allows matching the key with underscores replaced by any characters (like spaces)
        pattern = re.compile(r'\b' + r'.*'.join(re.escape(word) for word in key.split('_')) + r'\b', re.IGNORECASE)
        recipe_keywords.append((key, pattern))
        recipe_key_strings.append(key)

# Relation and conversation keywords from data.json
relation_keywords = list(data.get('relation_responses', {}).keys())
conversation_keywords = list(data.get('conversation_responses', {}).keys())

def find_recipe_by_keyword(key: str):
    for category in recipe_categories:
        if key in data['recipes'].get(category, {}):
            return data['recipes'][category][key]
    return None

def find_relation_response(keyword: str):
    return data.get('relation_responses', {}).get(keyword)

def find_conversation_response(keyword: str):
    return data.get('conversation_responses', {}).get(keyword)

class ChatRequest(BaseModel):
    message: str
    language: Optional[str] = "English"

@app.post("/api/chatbot/message")
async def chatbot_response(chat_request: ChatRequest):
    user_msg = chat_request.message.strip().lower()
    lang = chat_request.language if chat_request.language in ["English", "Hindi"] else "English"

    # 1. Greetings
    if user_msg in ["hi", "hello", "hey", "namaste", "नमस्ते"]:
        return {"response": "Hello! Ask me any family recipe or pooja ritual. 😊"}

    # 2. Check aliases first (full word match)
    for alias_key, mapped_key in aliases.items():
        if re.search(r'\b' + re.escape(alias_key) + r'\b', user_msg):
            recipe = find_recipe_by_keyword(mapped_key)
            if recipe:
                return format_recipe_response(recipe, mapped_key, lang)

            # Also check relation and conversation responses if any
            rel_resp = find_relation_response(mapped_key)
            if rel_resp:
                return {"response": rel_resp.get(lang, rel_resp.get("English"))}
            conv_resp = find_conversation_response(mapped_key)
            if conv_resp:
                return {"response": conv_resp.get(lang, conv_resp.get("English"))}

    # 3. Check relation keywords
    for rel_key in relation_keywords:
        if re.search(r'\b' + re.escape(rel_key) + r'\b', user_msg):
            res = find_relation_response(rel_key)
            if res:
                return {"response": res.get(lang, res.get("English"))}

    # 4. Check conversation keywords
    for conv_key in conversation_keywords:
        if re.search(r'\b' + re.escape(conv_key) + r'\b', user_msg):
            res = find_conversation_response(conv_key)
            if res:
                return {"response": res.get(lang, res.get("English"))}

    # 5. Regex pattern matching for recipes
    for key, pattern in recipe_keywords:
        if pattern.search(user_msg):
            recipe = find_recipe_by_keyword(key)
            return format_recipe_response(recipe, key, lang)

    # 6. Fuzzy matching fallback (with cutoff 0.6)
    close_matches = difflib.get_close_matches(user_msg.replace(" ", "_"), recipe_key_strings, n=1, cutoff=0.6)
    if close_matches:
        key = close_matches[0]
        recipe = find_recipe_by_keyword(key)
        return format_recipe_response(recipe, key, lang)

    # 7. Fallback response when nothing matches
    fallback = {
        "English": "Sorry, I couldn't find anything related. Can you try asking differently?",
        "Hindi": "माफ़ कीजिए, मुझे इस बारे में जानकारी नहीं मिली। कृपया कुछ और पूछें।"
    }
    return {"response": fallback[lang]}

def format_recipe_response(recipe, key, lang):
    if not recipe:
        return {"response": "Recipe not found."}

    title = recipe.get('title', {}).get(lang, recipe.get('title', {}).get('English', 'Recipe'))
    ingredients = recipe.get('ingredients', {}).get(lang, [])
    method = recipe.get('method', {}).get(lang, [])
    details = recipe.get('details', {}).get(lang, [])
    tip = recipe.get('tip', {}).get(lang)

    response_text = f"**{title}**\n\n"
    if ingredients:
        response_text += "Ingredients:\n" + "\n".join(f"- {item}" for item in ingredients) + "\n\n"
    if method:
        response_text += "Method:\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(method)) + "\n\n"
    if details:
        response_text += "Details:\n" + "\n".join(details) + "\n\n"
    if tip:
        response_text += "Tip:\n" + tip

    return {"response": response_text.strip()}
