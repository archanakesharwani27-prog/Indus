import sounddevice as sd
import numpy as np

print('Default output device:', sd.default.device)
print('Output devices:')
for i, dev in enumerate(sd.query_devices()):
    if dev['max_output_channels'] > 0:
        print(f'  {i}: {dev["name"]} (out={dev["max_output_channels"]})')

# Test playing
try:
    audio = np.zeros(24000, dtype=np.int16)
    sd.play(audio, samplerate=24000, dtype='int16')
    sd.wait()
    print('Playback: OK')
except Exception as e:
    print(f'Playback FAILED: {e}')