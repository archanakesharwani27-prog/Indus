import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from core.voice.gemini_live import GeminiLiveClient

async def test():
    print("Creating client...")
    client = GeminiLiveClient(
        api_key=os.getenv("GEMINI_API_KEY"),
        voice="Aoede",
        persona="zoya",
        input_device_index=1,
    )
    print("Running...")
    await client.run()

asyncio.run(test())