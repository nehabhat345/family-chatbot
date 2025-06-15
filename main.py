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

class ChatRequest(BaseModel):
    message: str
    language: Optional[str] = "English"  # "English" or "Hindi"

# Load data.json
DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
with open(DATA_FILE, "r", encoding="utf-8") as f:
    DATA = json.load(f)

# Map keywords to keys in data.json (include Hindi & English keywords)
KEYWORDS_MAP = {
    "karwa chauth": "karwa_chauth",
    "karwachauth": "karwa_chauth",
    "गोवर्धन": "gowardhan",
    "gowardhan": "gowardhan",
    "mathri": "mathri_recipe",
    "मठरी": "mathri_recipe",
    "mummy mathri": "mathri_recipe",
    "urad dal poori": "urad_dal_poori",
    "उड़द दाल पूड़ी": "urad_dal_poori",
    "bittergourd": "bittergourd_recipe",
    "karela": "bittergourd_recipe",
    "करेला": "bittergourd_recipe",
    "pumpkin": "pumpkin_recipe",
    "kaddu": "pumpkin_recipe",
    "कद्दू": "pumpkin_recipe",
}

# Basic conversational intents mapping (both Hindi & English)
CONVERSATION_RESPONSES = {
    "hello": {
        "English": "Hello! How can I help you today?",
        "Hindi": "नमस्ते! मैं आपकी कैसे मदद कर सकती हूँ?"
    },
    "hi": {
        "English": "Hi there! What would you like to know?",
        "Hindi": "हेलो! आप क्या जानना चाहेंगे?"
    },
    "how are you": {
        "English": "I'm good, thank you! How about you?",
        "Hindi": "मैं ठीक हूँ, धन्यवाद! आप कैसे हैं?"
    },
    "thank you": {
        "English": "You're welcome! Feel free to ask anything else.",
        "Hindi": "आपका स्वागत है! कुछ और पूछना हो तो बताइए।"
    },
    "bye": {
        "English": "Goodbye! Have a great day!",
        "Hindi": "अलविदा! आपका दिन शुभ हो!"
    }
}

def find_conversation_response(message: str, lang: str) -> Optional[str]:
    for key, responses in CONVERSATION_RESPONSES.items():
        if key in message:
            return responses.get(lang, responses.get("English"))
    return None

@app.post("/api/chatbot/message")
async def chatbot_message(request: ChatRequest):
    message = request.message.lower()
    lang = request.language.capitalize()  # Capitalize to match "English" or "Hindi"

    # Check for conversational queries first
    conv_response = find_conversation_response(message, lang)
    if conv_response:
        return {"response": conv_response}

    # Else try matching with keywords
    matched_key = None
    for kw, key in KEYWORDS_MAP.items():
        # Use regex word boundaries for better matching
        if re.search(r'\b' + re.escape(kw.lower()) + r'\b', message):
            matched_key = key
            break

    if not matched_key:
        # If nothing matched, fallback response
        fallback = {
            "English": "Sorry, I don't have information on that. You can ask me about recipes or festivals.",
            "Hindi": "माफ़ करें, मेरे पास इस विषय में जानकारी नहीं है। आप मुझसे व्यंजन या त्योहारों के बारे में पूछ सकते हैं।"
        }
        return {"response": fallback.get(lang, fallback["English"])}

    content = DATA.get(matched_key)
    if not content or lang not in content.get("title", {}):
        raise HTTPException(status_code=404, detail="Content not found in selected language.")

    title = content["title"].get(lang, "")
    
    # Build response based on available sections
    response_parts = [f"**{title}**\n"]

    # Details (list of steps)
    if "details" in content and lang in content["details"]:
        details = content["details"][lang]
        response_parts.append("\n".join([f"{i+1}. {step}" for i, step in enumerate(details)]))

    # Ingredients and method for recipes
    if "ingredients" in content and lang in content["ingredients"]:
        ingredients = content["ingredients"][lang]
        response_parts.append("\nIngredients:\n" + "\n".join(ingredients))

    if "method" in content and lang in content["method"]:
        method = content["method"][lang]
        response_parts.append("\nMethod:\n" + "\n".join([f"{i+1}. {m}" for i, m in enumerate(method)]))

    if "tip" in content and lang in content["tip"]:
        response_parts.append("\nTip:\n" + content["tip"][lang])

    response_text = "\n\n".join(response_parts)

    return {"response": response_text}
