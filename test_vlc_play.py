import sys, time, subprocess
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')
from core.system.windows import get_window_manager

movie_path = r"D:\Movies\The.Amazing.Spider.Man.2.2014.1080p.BluRay.Hindi.English.DD.5.1.x264.ESubs.Untouched.mkv"
vlc_path = r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"

# Launch VLC with proper arguments
print("Launching VLC with --play-and-exit --fullscreen...")
cmd = [vlc_path, "--play-and-exit", "--fullscreen", movie_path]
result = subprocess.Popen(cmd)
print("Started VLC with PID:", result.pid)

time.sleep(5)

wm = get_window_manager()
wm.refresh()
for w in wm.list_windows(""):
    try:
        if "vlc" in w.title.lower() or "vlc" in w.process_name.lower():
            print("VLC window:", w.title, "| PID:", w.process_id)
    except:
        pass

# Check if video is actually playing by looking for window title with movie name
time.sleep(3)
wm.refresh()
for w in wm.list_windows(""):
    try:
        if "spider" in w.title.lower() or "amazing" in w.title.lower():
            print("Movie window:", w.title)
    except:
        pass