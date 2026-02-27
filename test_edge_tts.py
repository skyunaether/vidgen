import asyncio
import edge_tts

async def test_tts():
    text = "Hello, this is a test of edge-tts."
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    try:
        await communicate.save("test_output.mp3")
        print("Success! Saved test_output.mp3")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_tts())
