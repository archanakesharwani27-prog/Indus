import os
os.environ['NVIDIA_API_KEY'] = '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'
os.environ['PROVIDER'] = 'nvidia'
os.environ['CHAT_PERSONA'] = 'assistant'

from providers.nvidia_provider import NVIDIAProvider
from core.memory import Memory
from core.chat_engine import ChatEngine
from core.voice.groq_tts import TTSClient

provider = NVIDIAProvider(persona='assistant')
memory = Memory(db_path='indus.db')
engine = ChatEngine(provider=provider, memory=memory, persona='assistant')
tts = TTSClient(voice='Arista')

# Test
reply = engine.respond('hello')
print(f'Reply: {reply}')
tts.speak(reply)
print('TTS done')
engine.shutdown()