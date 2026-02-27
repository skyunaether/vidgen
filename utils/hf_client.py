import os
import time
import base64
from typing import Dict, Any, Optional
from huggingface_hub import InferenceClient

def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

class HFClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("HF_TOKEN")
        if not self.token:
            raise ValueError("HF_TOKEN environment variable is not set.")
        self.client = InferenceClient(token=self.token)

    def chat_completion(self, model: str, system_prompt: str, user_prompt: str, max_retries: int = 3) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat_completion(
                    model=model,
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to get response after {max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def transcribe_audio(self, audio_path: str, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            try:
                result = self.client.automatic_speech_recognition(audio=audio_path, model="openai/whisper-large-v3-turbo")
                return result.text
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to transcribe audio after {max_retries} attempts: {e}")
                time.sleep(2 ** attempt)

    def vision_completion(self, model: str, system_prompt: str, user_prompt: str, image_paths: list[str], max_retries: int = 3) -> str:
        content = [{"type": "text", "text": user_prompt}]
        for path in image_paths:
            base64_img = _encode_image(path)
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}})
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat_completion(
                    model=model,
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to get vision response after {max_retries} attempts: {e}")
                time.sleep(2 ** attempt)

def get_hf_client() -> HFClient:
    return HFClient()
