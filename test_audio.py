import pyaudio
p = pyaudio.PyAudio()

# Check default output device info
try:
    default_out = p.get_default_output_device_info()
    print('Default output device info:', default_out)
except Exception as e:
    print('No default output device:', e)

# Try to use host API
for i in range(p.get_host_api_count()):
    info = p.get_host_api_info_by_index(i)
    print(f'Host API {i}: {info}')
    for j in range(info['deviceCount']):
        dev_info = p.get_device_info_by_host_api_device_index(i, j)
        if dev_info['maxOutputChannels'] > 0:
            print(f'  Device {dev_info["index"]}: {dev_info["name"]} (out={dev_info["maxOutputChannels"]})')

p.terminate()