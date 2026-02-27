import json
import time
from google import genai
from vidgen.config import Config

def test():
    config = Config.load()
    client = genai.Client(api_key=config.gemini_api_key)
    
    try:
        operation = client.models.generate_videos(
            model='veo-2.0-generate-001',
            prompt="A cinematic panning shot of a glowing rat in a neon city, highly detailed, 4k"
        )
        print(dir(operation))
        print("name:", getattr(operation, "name", None))
        print("metadata:", getattr(operation, "metadata", None))
        print("response:", getattr(operation, "response", None))
        print("error:", getattr(operation, "error", None))
        print("done:", getattr(operation, "done", None))
        
        while not getattr(operation, "done", False):
            print("Operation not done yet. Fetching update...")
            time.sleep(5)
            # is there a client.operations.get?
            if hasattr(client, "operations"):
                operation = client.operations.get(operation=operation) # or operation.name
            else:
                # old SDK way: just re-fetch?
                pass
            print(f"done: {getattr(operation, 'done', None)}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
