from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
import re

app = FastAPI()

# Enable CORS for all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data.json at startup
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Flatten all recipe keys from all categories (pooja_rituals, satvik_recipes, kashmiri_dishes, general_recipes)
recipe_categories = ['pooja_rituals', 'satvik_recipes', 'kashmiri_dishes', 'general_recipes']
recipe_keywords = []

for category in recipe_categories:
    category_data = data.get(category, {})
    for key in category_data.keys():
        recipe_keywords.append(key.lower())

# Relation and conversation keywords (if present)
relation_keywords = list(data.get('relation_responses', {}).keys()) if 'relation_responses' in data else []
conversation_keywords = list(data.get('conversation_responses', {}).keys()) if 'conversation_responses' in data else []

def find_recipe_by_keyword(keyword: str):
    keyword = keyword.lower()
    for category in recipe_categories:
        category_data = data.get(category, {})
        if keyword in category_data:
            return category_data[keyword]
    return None

def find_relation_response(keyword: str):
    keyword = keyword.lower()
    return data.get('relation_responses', {}).get(keyword) if 'relation_responses' in data else None

def find_conversation_response(keyword: str):
    keyword = keyword.lower()
    return data.get('conversation_responses', {}).get(keyword) if 'conversation_responses' in data else None

class ChatRequest(BaseModel):
    message: str
    language: Optional[str] = "English"  # Default language English

@app.post("/api/chatbot/message")
async def chatbot_response(chat_request: ChatRequest):
    user_msg = chat_request.message.strip().lower()
    lang = chat_request.language if chat_request.language in ["English", "Hindi"] else "English"

    # 1. Check if user message contains any relation keywords
    for rel_key in relation_keywords:
        if re.search(r'\b' + re.escape(rel_key) + r'\b', user_msg):
            response = find_relation_response(rel_key)
            if response:
                return {"response": response.get(lang, response.get("English", "Sorry, no response available."))}

    # 2. Check if user message matches a conversation response keyword
    for conv_key in conversation_keywords:
        if re.search(r'\b' + re.escape(conv_key) + r'\b', user_msg):
            response = find_conversation_response(conv_key)
            if response:
                return {"response": response.get(lang, response.get("English", "Sorry, no response available."))}

    # 3. Check if user message contains any recipe keywords
    for rec_key in recipe_keywords:
        if re.search(r'\b' + re.escape(rec_key) + r'\b', user_msg):
            recipe = find_recipe_by_keyword(rec_key)
            if recipe:
                title = recipe.get('title', {}).get(lang, recipe.get('title', {}).get('English', 'Recipe'))
                ingredients = recipe.get('ingredients', {}).get(lang, [])
                method = recipe.get('method', {}).get(lang, [])
                details = recipe.get('details', {}).get(lang, [])
                tip = recipe.get('tip', {}).get(lang, None)

                # Prepare response text
                response_text = f"**{title}**\n\n"
                if ingredients:
                    response_text += "Ingredients:\n" + "\n".join(f"- {item}" for item in ingredients) + "\n\n"
                if method:
                    response_text += "Method:\n" + "\n".join(f"{idx+1}. {step}" for idx, step in enumerate(method)) + "\n\n"
                if details:
                    response_text += "Details:\n" + "\n".join(details) + "\n\n"
                if tip:
                    response_text += f"Tip:\n{tip}\n"

                return {"response": response_text.strip()}

    # Default fallback response
    fallback_responses = {
        "English": "Sorry, I couldn't find information on that. Could you please ask about something else?",
        "Hindi": "माफ़ करें, मुझे उस बारे में जानकारी नहीं मिली। कृपया कुछ और पूछें।"
    }
    return {"response": fallback_responses.get(lang, fallback_responses["English"])}
