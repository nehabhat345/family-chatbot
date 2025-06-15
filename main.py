from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os

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
    language: Optional[str] = "English"  # Note: matches keys in JSON exactly

# Load data.json
DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
with open(DATA_FILE, "r", encoding="utf-8") as f:
    DATA = json.load(f)

# Map keywords to keys in data.json
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

@app.post("/api/chatbot/message")
async def chatbot_message(request: ChatRequest):
    message = request.message.lower()
    lang = request.language.capitalize()  # Capitalize to match "English" or "Hindi"

    # Find matched key from keywords
    matched_key = None
    for kw, key in KEYWORDS_MAP.items():
        if kw in message:
            matched_key = key
            break

    if not matched_key:
        return {
            "response": "Sorry, I don't have information on that. Please ask about Karwa Chauth, Gowardhan, Mathri recipe, or Urad Dal Poori."
        }

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
