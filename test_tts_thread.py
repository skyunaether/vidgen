import threading
import asyncio
from pathlib import Path
from vidgen.ttsgen import _edge_tts_to_mp3, _mp3_duration

def run_tts_in_thread():
    print("Thread started.")
    test_file = Path("test_thread.mp3")
    try:
        _edge_tts_to_mp3("Testing edge tts inside a sub-thread.", test_file)
        dur = _mp3_duration(test_file)
        print(f"Thread finished: exists={test_file.exists()}, dur={dur}")
    except Exception as e:
        print(f"Error in thread: {e}")

if __name__ == "__main__":
    t = threading.Thread(target=run_tts_in_thread)
    t.start()
    t.join()
