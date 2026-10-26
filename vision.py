"""Send a photo to Gemini and get back a validated list of dishes."""
import base64
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"),
                      http_options={"retry_options": {"attempts": 2, "http_status_codes": [503]}})
MODEL = "gemini-flash-latest"

MENU = list(json.loads(Path("data/menu.json").read_text(encoding="utf-8"))["dishes"])
UNITS = ["katori", "cup", "piece", "tbsp"]

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dish": {"type": "string"},
                    "alternatives": {"type": "array", "items": {"type": "string"}},
                    "amount": {"type": "number"},
                    "unit": {"type": "string", "enum": UNITS},
                    "confidence": {"type": "number"},
                },
                "required": ["dish", "alternatives", "amount", "unit", "confidence"],
            },
        },
        "other_diners": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["items", "other_diners"],
}

PROMPT = """You are logging ONE person's meal from a photo of an Indian thali.

List every food item on the main plate, including the bowls (katoris) on it.
If another person's plate or bowl is in the photo, do not list its food under
items; name it under other_diners instead.

For each item:
- dish: choose from the allowed names. If nothing fits, use "unknown".
- alternatives: up to 3 other allowed names it could be, most likely first.
- amount and unit: katori for a bowl, cup for rice, piece for rotis, puris,
  papads and sweets (count them), tbsp for pickle, chutney or salad garnish.
- confidence: from 0 to 1, how sure you are of the dish name.

Allowed dish names:
""" + ", ".join(MENU)

def ask_gemini(photo_path):
    photo = base64.b64encode(Path(photo_path).read_bytes()).decode()
    return client.interactions.create(
        model=MODEL,
        input=[
            {"type": "text", "text": PROMPT},
            {"type": "image", "data": photo, "mime_type": "image/jpeg"},
        ],
        response_format={"type": "text", "mime_type": "application/json", "schema": SCHEMA},
        timeout=180,
    )

def read_photo(photo_path):
    """Return the model's reading of a photo, asking Gemini only the first time."""
    record = Path("records") / (Path(photo_path).stem + ".json")
    if record.exists():
        return json.loads(record.read_text(encoding="utf-8"))
    reply = ask_gemini(photo_path)
    saved = {
        "photo": Path(photo_path).name,
        "model": reply.model,
        "tokens": {"in": reply.usage.total_input_tokens,
                   "out": reply.usage.total_output_tokens,
                   "thinking": reply.usage.total_thought_tokens},
        "reading": json.loads(reply.output_text),
    }
    record.parent.mkdir(exist_ok=True)
    record.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    return saved

def validate(reading):
    """Keep the items that follow the rules; describe the ones that don't."""
    good, problems = [], []
    for item in reading.get("items", []):
        if item.get("dish") not in MENU + ["unknown"]:
            problems.append(f"not on the menu, marked unknown: {item.get('dish')}")
            item["model_said"], item["dish"] = item.get("dish"), "unknown"
        if item.get("unit") not in UNITS:
            problems.append(f"{item['dish']}: unit not allowed: {item.get('unit')}")
        elif not 0 < item.get("amount", 0) <= 20:
            problems.append(f"{item['dish']}: amount out of range: {item.get('amount')}")
        elif not 0 <= item.get("confidence", -1) <= 1:
            problems.append(f"{item['dish']}: confidence out of range: {item.get('confidence')}")
        else:
            item["alternatives"] = [a for a in item.get("alternatives", []) if a in MENU][:3]
            good.append(item)
    return good, problems

def show(photo_path):
    saved = read_photo(photo_path)
    items, problems = validate(saved["reading"])
    for item in items:
        maybe = "   (or: " + " or ".join(item["alternatives"]) + ")" if item["alternatives"] else ""
        print(f"{item['dish']:24} {item['amount']:>4} {item['unit']:7} "
              f"sure: {item['confidence']:.0%}{maybe}")
    for p in problems:
        print("PROBLEM:", p)
    if saved["reading"]["other_diners"]:
        print("Left out (someone else's):", ", ".join(saved["reading"]["other_diners"]))

def record_all():
    """Read every photo in photos/, skipping ones already saved. Run again tomorrow to finish."""
    for photo in sorted(Path("photos").glob("*.jpg")):
        if (Path("records") / (photo.stem + ".json")).exists():
            continue
        try:
            read_photo(photo)
            print("saved", photo.name)
        except Exception as e:
            print("stopped at", photo.name, "-", e)
            print("Nothing is lost. Run this again later to carry on.")
            return
    print("all photos recorded")


if __name__ == "__main__":
    if sys.argv[1] == "--all":
        record_all()
    else:
        show(sys.argv[1])
