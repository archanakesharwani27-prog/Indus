import sounddevice as sd
import numpy as np

print('Default output device:', sd.default.device)
print('Output devices:')
for i, dev in enumerate(sd.query_devices()):
    if dev['max_output_channels'] > 0:
        print(f'  {i}: {dev["name"]} (out={dev["max_output_channels"]})')

# Test playing with explicit device
for dev_idx in [5, 7, 9]:
    try:
        print(f'Testing device {dev_idx}...')
        audio = np.zeros(24000, dtype=np.int16)
        sd.play(audio, samplerate=24000, device=dev_idx, blocking=True)
        print(f'  Device {dev_idx}: OK')
    except Exception as e:
        print(f'  Device {dev_idx}: FAILED - {e}')

# Try default device
try:
    print('Testing default device...')
    audio = np.zeros(24000, dtype=np.int16)
    sd.play(audio, samplerate=24000, blocking=True)
    print('  Default: OK')
except Exception as e:
    print(f'  Default: FAILED - {e}')