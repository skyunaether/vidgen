import os
from google import genai

client = genai.Client()

models = client.models.list()
for model in models:
    if "veo" in model.name.lower() or "video" in model.name.lower():
        print(f"Model: {model.name}")
        print(f"  Supported generation methods: {model.supported_generation_methods}")
