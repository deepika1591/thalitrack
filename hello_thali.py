import base64
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

with open("photos/05_traditional_bengali_thali_1.jpg", "rb") as f:    photo = base64.b64encode(f.read()).decode()

reply = client.interactions.create(
    model="gemini-flash-latest",
    input=[
        {"type": "text", "text": "What is on this plate? List each dish and how much there is."},
        {"type": "image", "data": photo, "mime_type": "image/jpeg"},
    ])

print(reply.output_text)
print(reply.usage.total_input_tokens, "in,",
      reply.usage.total_output_tokens, "out,",
      reply.usage.total_thought_tokens, "thinking")