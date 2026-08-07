import pyaudio
p = pyaudio.PyAudio()
print('Input devices:')
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f'  {i}: {info["name"]} (in={info["maxInputChannels"]})')
print()
print('Output devices:')
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxOutputChannels'] > 0:
        print(f'  {i}: {info["name"]} (out={info["maxOutputChannels"]})')
p.terminate()