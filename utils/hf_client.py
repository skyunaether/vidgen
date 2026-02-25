import os
import time
from typing import Dict, Any, Optional
from huggingface_hub import InferenceClient

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

def get_hf_client() -> HFClient:
    return HFClient()
