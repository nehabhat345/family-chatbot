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

# Flatten all recipe keys for regex matching
recipe_keywords = []
for category, recipes in data['recipes'].items():
    for key in recipes.keys():
        recipe_keywords.append(key.lower())

# Relation keywords
relation_keywords = list(data.get('relation_responses', {}).keys())

# Conversation keywords
conversation_keywords = list(data.get('conversation_responses', {}).keys())

def find_recipe_by_keyword(keyword: str):
    keyword = keyword.lower()
    for category, recipes in data['recipes'].items():
        if keyword in recipes:
            return recipes[keyword]
    return None

def find_relation_response(keyword: str):
    keyword = keyword.lower()
    return data.get('relation_responses', {}).get(keyword)

def find_conversation_response(keyword: str):
    keyword = keyword.lower()
    return data.get('conversation_responses', {}).get(keyword)

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
                title = recipe['title'].get(lang, recipe['title'].get('English', 'Recipe'))
                ingredients = recipe.get('ingredients', {}).get(lang, [])
                method = recipe.get('method', {}).get(lang, [])
                details = recipe.get('details', {}).get(lang, [])
                # Prepare response text
                response_text = f"**{title}**\n\n"
                if ingredients:
                    response_text += "Ingredients:\n" + "\n".join(f"- {item}" for item in ingredients) + "\n\n"
                if method:
                    response_text += "Method:\n" + "\n".join(f"{idx+1}. {step}" for idx, step in enumerate(method)) + "\n"
                if details:
                    response_text += "Details:\n" + "\n".join(details) + "\n"
                return {"response": response_text.strip()}

    # Default fallback response
    fallback_responses = {
        "English": "Sorry, I couldn't find information on that. Could you please ask about something else?",
        "Hindi": "माफ़ करें, मुझे उस बारे में जानकारी नहीं मिली। कृपया कुछ और पूछें।"
    }
    return {"response": fallback_responses.get(lang, fallback_responses["English"])}
