from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
import re
import difflib

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

recipe_categories = ['pooja_rituals', 'satvik_recipes', 'kashmiri_dishes', 'general_recipes']

# Recipe keyword setup
recipe_keywords = []
recipe_key_strings = []

for category in recipe_categories:
    for key in data['recipes'].get(category, {}):
        recipe_keywords.append((key, re.compile(r'\b' + r'.*'.join(re.escape(word) for word in key.split('_')) + r'\b', re.IGNORECASE)))
        recipe_key_strings.append(key)

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

    # 2. Relation
    for rel_key in relation_keywords:
        if re.search(r'\b' + re.escape(rel_key) + r'\b', user_msg):
            res = find_relation_response(rel_key)
            if res:
                return {"response": res.get(lang, res.get("English"))}

    # 3. Conversations
    for conv_key in conversation_keywords:
        if re.search(r'\b' + re.escape(conv_key) + r'\b', user_msg):
            res = find_conversation_response(conv_key)
            if res:
                return {"response": res.get(lang, res.get("English"))}

    # 4. Regex recipe match
    for key, pattern in recipe_keywords:
        if pattern.search(user_msg):
            recipe = find_recipe_by_keyword(key)
            return format_recipe_response(recipe, key, lang)

    # 5. Fuzzy match fallback
    close_matches = difflib.get_close_matches(user_msg.replace(" ", "_"), recipe_key_strings, n=1, cutoff=0.6)
    if close_matches:
        key = close_matches[0]
        recipe = find_recipe_by_keyword(key)
        return format_recipe_response(recipe, key, lang)

    # 6. Fallback
    fallback = {
        "English": "Sorry, I couldn't find anything related. Can you try asking differently?",
        "Hindi": "माफ़ कीजिए, मुझे इस बारे में जानकारी नहीं मिली। कृपया कुछ और पूछें।"
    }
    return {"response": fallback[lang]}

def format_recipe_response(recipe, key, lang):
    if not recipe:
        return {"response": "Recipe not found."}

    title = recipe['title'].get(lang, recipe['title'].get('English', 'Recipe'))
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
