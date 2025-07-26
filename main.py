from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
import re
import difflib
from langdetect import detect

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

recipe_categories = ['pooja_rituals', 'satvik_recipes', 'kashmiri_dishes', 'general_recipes']

aliases = {
    "karwa chauth": "karwa_chauth",
    "karwa chauth pooja": "karwa_chauth",
    "karwachauth": "karwa_chauth",
    "karva chauth": "karwa_chauth",
    "karwachauth pooja": "karwa_chauth",
    
    "teej": "teej_pooja",
    "teej pooja": "teej_pooja",
    "hariyali teej": "teej_pooja",
    "teej vrat": "teej_pooja",
    "teej ritual": "teej_pooja",


    "gowardhan pooja": "gowardhan_pooja",
    "govardhan pooja": "gowardhan_pooja",

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

    "haak": "haak",
    "haak recipe": "haak",
    "hak": "haak",
    "kashmiri haak": "haak",
    "kashmiri hak": "haak",

    "fried rice": "fried_rice",
    "friend rice": "fried_rice",

    "food": "food_general",
    "food recipe": "food_general",
    "recipes": "food_general"
}

recipe_keywords = []
recipe_key_strings = []

for category in recipe_categories:
    for key in data['recipes'].get(category, {}):
        pattern = re.compile(r'\b' + r'.*'.join(re.escape(word) for word in key.split('_')) + r'\b', re.IGNORECASE)
        recipe_keywords.append((key, pattern))
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
    language: Optional[str] = None

def format_recipe_response(recipe, key, lang):
    if not recipe:
        return {"response": f"Sorry, I couldn't find the recipe for '{key.replace('_', ' ')}'."}

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

@app.post("/api/chatbot/message")
async def chatbot_response(chat_request: ChatRequest):
    user_msg = chat_request.message.strip().lower()
    lang = chat_request.language

    if not lang:
        try:
            lang_code = detect(user_msg)
        except:
            lang_code = "en"
        lang = "Hindi" if lang_code == "hi" else "English"

    if lang not in ["English", "Hindi"]:
        lang = "English"

    greetings = ["hi", "hello", "hey", "namaste", "नमस्ते"]
    if any(g == user_msg or f" {g} " in f" {user_msg} " for g in greetings):
        greet_msg = {
            "English": "Hello! I'm Nehu 😊 Ask me any family recipe or pooja ritual.",
            "Hindi": "नमस्ते! मैं नेहू हूँ 😊 मुझसे कोई भी पारिवारिक रेसिपी या पूजा विधि पूछें।"
        }
        return {"response": greet_msg[lang]}

    yes_words = {"yes", "yeah", "yup", "haan", "हाँ", "yes please", "of course"}
    no_words = {"no", "nah", "nope", "nahi", "नहीं", "na"}

    if user_msg in yes_words:
        yes_resp = {
            "English": "Great! How else can I help you? You can ask for recipes or pooja rituals.",
            "Hindi": "बहुत अच्छा! मैं और कैसे मदद कर सकती हूँ? आप मुझसे रेसिपी या पूजा विधि पूछ सकते हैं।"
        }
        return {"response": yes_resp[lang]}

    if user_msg in no_words:
        no_resp = {
            "English": "Alright. If you need anything else, just ask!",
            "Hindi": "ठीक है। अगर आपको और कुछ चाहिए तो बस पूछिए।"
        }
        return {"response": no_resp[lang]}

    # General keywords and synonyms for broader matches
    general_topic_keywords = {
        "food": ["food", "khana", "khana peena", "khana-pina", "dish", "recipes", "recipe", "cooking", "cuisine"],
        "pooja": ["pooja", "puja", "ritual", "vidhi", "prayer", "havan", "aarti"],
        "culture": ["culture", "tradition", "parampara", "custom", "heritage", "sanskaar"],
        "family": ["family", "ghar", "ghar ki baat", "rishtay", "relations"],
    }

    for topic, keywords in general_topic_keywords.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', user_msg):
                general_resp = {
                    "food": {
                        "English": "I can share family recipes including Satvik, Kashmiri, and general dishes. What would you like to try?",
                        "Hindi": "मैं पारिवारिक रेसिपी जैसे सात्विक, कश्मीरी, और सामान्य व्यंजन बता सकती हूँ। आप क्या जानना चाहेंगे?"
                    },
                    "pooja": {
                        "English": "I can guide you through various pooja rituals like Karwa Chauth and Govardhan Pooja. What would you like to know?",
                        "Hindi": "मैं आपको करवा चौथ और गोवर्धन पूजा जैसी पूजा विधियों के बारे में बता सकती हूँ। आप क्या जानना चाहेंगे?"
                    },
                    "culture": {
                        "English": "Our family's culture and traditions are rich! Feel free to ask about rituals, festivals, or recipes.",
                        "Hindi": "हमारे परिवार की संस्कृति और परंपराएं बहुत समृद्ध हैं! पूजा, त्योहार या रेसिपी के बारे में पूछें।"
                    },
                    "family": {
                        "English": "I can share stories, recipes, and rituals related to family traditions. What interests you?",
                        "Hindi": "मैं परिवार की परंपराओं से जुड़ी कहानियाँ, रेसिपी और पूजा विधियाँ साझा कर सकती हूँ। आप क्या जानना चाहेंगे?"
                    }
                }
                return {"response": general_resp[topic][lang]}

    # Exact alias match
    if user_msg in aliases:
        mapped_key = aliases[user_msg]
        recipe = find_recipe_by_keyword(mapped_key)
        if recipe:
            return format_recipe_response(recipe, mapped_key, lang)
        rel_resp = find_relation_response(mapped_key)
        if rel_resp:
            return {"response": rel_resp.get(lang)}
        conv_resp = find_conversation_response(mapped_key)
        if conv_resp:
            return {"response": conv_resp.get(lang)}

    # Regex alias match
    for alias_key, mapped_key in aliases.items():
        if re.search(r'\b' + re.escape(alias_key) + r'\b', user_msg):
            recipe = find_recipe_by_keyword(mapped_key)
            if recipe:
                return format_recipe_response(recipe, mapped_key, lang)
            rel_resp = find_relation_response(mapped_key)
            if rel_resp:
                return {"response": rel_resp.get(lang)}
            conv_resp = find_conversation_response(mapped_key)
            if conv_resp:
                return {"response": conv_resp.get(lang)}

    # Relation match
    for rel_key in relation_keywords:
        if re.search(r'\b' + re.escape(rel_key) + r'\b', user_msg):
            res = find_relation_response(rel_key)
            if res:
                return {"response": res.get(lang)}

    # Conversation match
    for conv_key in conversation_keywords:
        if re.search(r'\b' + re.escape(conv_key) + r'\b', user_msg):
            res = find_conversation_response(conv_key)
            if res:
                return {"response": res.get(lang)}

    # Recipe match by pattern
    for key, pattern in recipe_keywords:
        if pattern.search(user_msg):
            recipe = find_recipe_by_keyword(key)
            return format_recipe_response(recipe, key, lang)

    # Fuzzy match recipe key
    close_matches = difflib.get_close_matches(user_msg.replace(" ", "_"), recipe_key_strings, n=1, cutoff=0.6)
    if close_matches:
        key = close_matches[0]
        recipe = find_recipe_by_keyword(key)
        return format_recipe_response(recipe, key, lang)

    # Fuzzy alias suggestion with extra guidance
    alias_keys = list(aliases.keys())
    typo_suggestions = difflib.get_close_matches(user_msg.strip(), alias_keys, n=1, cutoff=0.7)
    if typo_suggestions and typo_suggestions[0].lower() != user_msg:
        suggestion = typo_suggestions[0]
        correction_msg = {
            "English": (
                f"Did you mean **'{suggestion}'**?\n"
                "You can ask me about Satvik, Kashmiri, Pooja rituals, or general family recipes."
            ),
            "Hindi": (
                f"क्या आप **'{suggestion}'** कहना चाह रहे थे?\n"
                "आप मुझसे सात्विक, कश्मीरी, पूजा विधि या सामान्य पारिवारिक रेसिपी पूछ सकते हैं।"
            )
        }
        return {
            "response": correction_msg[lang],
            "suggested_keyword": suggestion
        }

    fallback_msg = {
        "English": "Sorry, I couldn't find anything related. Can you try asking differently?",
        "Hindi": "माफ़ कीजिए, मुझे इस बारे में जानकारी नहीं मिली। कृपया कुछ और पूछें।"
    }
    return {"response": fallback_msg[lang]}
