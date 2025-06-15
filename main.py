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

# Keywords with regex patterns
KEYWORDS_PATTERNS = [
    (re.compile(r"\bkarwa\s?chauth\b"), "karwa_chauth"),
    (re.compile(r"\bkarwachauth\b"), "karwa_chauth"),
    (re.compile(r"\bगोवर्धन\b"), "gowardhan"),
    (re.compile(r"\bgowardhan\b"), "gowardhan"),
    (re.compile(r"\bmathri\b"), "mathri_recipe"),
    (re.compile(r"\bमठरी\b"), "mathri_recipe"),
    (re.compile(r"\bmummy\s+mathri\b"), "mathri_recipe"),
    (re.compile(r"\burad\s+dal\s+poori\b"), "urad_dal_poori"),
    (re.compile(r"\bउड़द\s+दाल\s+पूड़ी\b"), "urad_dal_poori"),
    (re.compile(r"\bbittergourd\b"), "bittergourd_recipe"),
    (re.compile(r"\bkarela\b"), "bittergourd_recipe"),
    (re.compile(r"\bकरेला\b"), "bittergourd_recipe"),
    (re.compile(r"\bpumpkin\b"), "pumpkin_recipe"),
    (re.compile(r"\bkaddu\b"), "pumpkin_recipe"),
    (re.compile(r"\bकद्दू\b"), "pumpkin_recipe"),
]

# Conversational patterns
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

# Family relation responses
RELATION_RESPONSES = {
    "mummy": {
        "English": "Mummy always makes the best food, doesn't she?",
        "Hindi": "मम्मी का खाना हमेशा सबसे अच्छा होता है, है ना?"
    },
    "mom": {
        "English": "Mom’s love is the secret ingredient in every recipe.",
        "Hindi": "माँ का प्यार हर रेसिपी में छुपा हुआ स्वाद होता है।"
    },
    "chachi": {
        "English": "Chachi must have some amazing recipes too!",
        "Hindi": "चाची के पास भी जरूर कुछ लाजवाब रेसिपी होंगी!"
    },
    "didi": {
        "English": "Didi always knows the kitchen hacks!",
        "Hindi": "दीदी को तो सभी किचन टिप्स पता होती हैं!"
    },
    "papa": {
        "English": "Papa always appreciates good food!",
        "Hindi": "पापा को अच्छा खाना बहुत पसंद होता है!"
    },
    "bhabhi": {
        "English": "Bhabhi cooks with so much love!",
        "Hindi": "भाभी बहुत प्यार से खाना बनाती हैं!"
    },
    "nani": {
        "English": "Nani’s recipes are pure gold.",
        "Hindi": "नानी की रेसिपी खज़ाने की तरह होती हैं।"
    },
    "dadi": {
        "English": "Dadi ke haath ka swaad alag hi hota hai!",
        "Hindi": "दादी के हाथ का स्वाद ही कुछ और होता है!"
    },
    "bua": {
        "English": "Bua's food has that special traditional touch!",
        "Hindi": "बुआ के खाने में एक खास पारंपरिक स्वाद होता है!"
    }
}

def find_conversation_response(message: str, lang: str) -> Optional[str]:
    for pattern, responses in CONVERSATION_RESPONSES.items():
        if re.search(r'\b' + re.escape(pattern) + r'\b', message):
            return responses.get(lang, responses.get("English"))
    return None

def find_relation_response(message: str, lang: str) -> Optional[str]:
    for relation, responses in RELATION_RESPONSES.items():
        if re.search(r'\b' + re.escape(relation) + r'\b', message):
            return responses.get(lang, responses.get("English"))
    return None

@app.post("/api/chatbot/message")
async def chatbot_message(request: ChatRequest):
    message = request.message.lower()
    lang = request.language.capitalize()

    # 1. Check if message contains a family relation
    relation_response = find_relation_response(message, lang)
    if relation_response:
        return {"response": relation_response}

    # 2. Check for general conversational keywords
    conv_response = find_conversation_response(message, lang)
    if conv_response:
        return {"response": conv_response}

    # 3. Match against recipe/festival keywords using regex
    matched_key = None
    for pattern, key in KEYWORDS_PATTERNS:
        if pattern.search(message):
            matched_key = key
            break

    if not matched_key:
        fallback = {
            "English": "Sorry, I don't have information on that. You can ask me about other recipes or festivals.",
            "Hindi": "माफ़ करें, मेरे पास इस विषय में जानकारी नहीं है। आप मुझसे व्यंजन या त्योहारों के बारे में पूछ सकते हैं।"
        }
        return {"response": fallback.get(lang, fallback["English"])}

    content = DATA.get(matched_key)
    if not content or lang not in content.get("title", {}):
        raise HTTPException(status_code=404, detail="Content not found in selected language.")

    title = content["title"].get(lang, "")
    response_parts = [f"**{title}**\n"]

    if "details" in content and lang in content["details"]:
        details = content["details"][lang]
        response_parts.append("\n".join([f"{i+1}. {step}" for i, step in enumerate(details)]))

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
