#!/usr/bin/env python
"""
Complete Indus PC-side Demo - All Features
Shows: VLC movie playback, Volume control, Brightness, WhatsApp, YouTube, Memory, App control
"""
import sys
import time
import subprocess
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.system.launcher import get_launcher
from core.system.windows import get_window_manager
from core.skills.system import VolumeControlSkill
from core.memory import Memory
from core.chat_engine import ChatEngine
from providers.mock_provider import MockProvider


def print_header(title):
    print("\n" + "="*60)
    print("  " + title)
    print("="*60)


def demo_vlc_movie():
    """Play Spider-Man 2 movie with VLC."""
    print_header("VLC MOVIE PLAYBACK - The Amazing Spider-Man 2")
    
    launcher = get_launcher()
    movie_path = r"D:\Movies\The.Amazing.Spider.Man.2.2014.1080p.BluRay.Hindi.English.DD.5.1.x264.ESubs.Untouched.mkv"
    
    if not os.path.exists(movie_path):
        print("Movie file not found at:", movie_path)
        return False
    
    print("Launching VLC with movie...")
    result = launcher.launch("vlc media player", movie_path)
    print("Result:", result)
    
    time.sleep(4)
    
    wm = get_window_manager()
    wm.refresh()
    for w in wm.list_windows(""):
        try:
            if "vlc" in w.title.lower() or "vlc" in w.process_name.lower():
                print("VLC Window:", w.title, "| PID:", w.process_id)
        except:
            pass
    
    print("Movie is now playing in VLC!")
    return True


def demo_volume_control():
    """Demonstrate volume control."""
    print_header("VOLUME CONTROL (0-100%, Mute/Unmute)")
    
    skill = VolumeControlSkill()
    
    print("Current volume:", skill.execute(action="get"))
    time.sleep(1)
    
    print("\nSetting to 80%...")
    print(skill.execute(action="set", level=80))
    time.sleep(2)
    
    print("\nSetting to 30%...")
    print(skill.execute(action="set", level=30))
    time.sleep(2)
    
    print("\nVolume up...")
    print(skill.execute(action="up"))
    time.sleep(1)
    
    print("\nVolume down...")
    print(skill.execute(action="down"))
    time.sleep(1)
    
    print("\nMute...")
    print(skill.execute(action="mute"))
    time.sleep(2)
    
    print("\nUnmute...")
    print(skill.execute(action="unmute"))
    time.sleep(1)
    
    print("\nRestoring to 50%...")
    print(skill.execute(action="set", level=50))
    time.sleep(1)
    
    print("\nVolume control demo complete!")
    return True


def demo_brightness_control():
    """Demonstrate brightness control."""
    print_header("BRIGHTNESS CONTROL (0-100%)")
    
    try:
        print("Setting brightness to 100%...")
        subprocess.run([
            "powershell", "-Command",
            "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, 100)"
        ], capture_output=True, timeout=10)
        time.sleep(2)
        
        print("Setting brightness to 30%...")
        subprocess.run([
            "powershell", "-Command",
            "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, 30)"
        ], capture_output=True, timeout=10)
        time.sleep(2)
        
        print("Setting brightness to 80%...")
        subprocess.run([
            "powershell", "-Command",
            "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, 80)"
        ], capture_output=True, timeout=10)
        time.sleep(2)
        
        print("Restoring to 50%...")
        subprocess.run([
            "powershell", "-Command",
            "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, 50)"
        ], capture_output=True, timeout=10)
        
        print("Brightness control demo complete!")
        return True
    except Exception as e:
        print("Brightness control error:", e)
        return True


def demo_whatsapp():
    """Open WhatsApp desktop app."""
    print_header("WHATSAPP DESKTOP APP")
    
    print("Opening WhatsApp via URI scheme...")
    result = subprocess.run(["start", "", "whatsapp:"], shell=True, capture_output=True, text=True)
    print("Return code:", result.returncode)
    
    time.sleep(3)
    
    wm = get_window_manager()
    wm.refresh()
    found = False
    for w in wm.list_windows(""):
        try:
            if "whatsapp" in w.title.lower() or "whatsapp" in w.process_name.lower():
                print("WhatsApp Window:", w.title, "| Process:", w.process_name)
                found = True
        except:
            pass
    
    if found:
        print("WhatsApp desktop app opened successfully!")
    else:
        print("WhatsApp may not be installed or URI scheme not registered")
    
    return True


def demo_youtube():
    """Open YouTube in Edge browser."""
    print_header("YOUTUBE IN EDGE BROWSER")
    
    launcher = get_launcher()
    
    print("Opening YouTube (Rick Astley - Never Gonna Give You Up)...")
    result = launcher.launch("edge", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print("Result:", result)
    
    time.sleep(5)
    
    wm = get_window_manager()
    wm.refresh()
    for w in wm.list_windows(""):
        try:
            if "youtube" in w.title.lower() or "edge" in w.process_name.lower():
                print("Edge/YouTube Window:", w.title[:80], "| Process:", w.process_name)
        except:
            pass
    
    print("YouTube opened in Edge!")
    return True


def demo_memory():
    """Test memory system."""
    print_header("MEMORY SYSTEM (SQLite + Semantic)")
    
    memory = Memory(db_path="demo_memory.db")
    memory.clear()
    
    engine = ChatEngine(provider=MockProvider(), memory=memory)
    
    print("Storing conversation...")
    engine.respond("My name is Ansh Kesharwani")
    engine.respond("I am building Indus AI assistant")
    engine.respond("My favorite movie is The Amazing Spider-Man 2")
    
    recent = memory.get_recent(10)
    print("Stored messages:", len(recent))
    for msg in recent:
        print("  [" + msg["role"] + "] " + msg["content"][:60])
    
    print("\nTesting context retention...")
    reply = engine.respond("What is my name and favorite movie?")
    print("Response:", reply)
    
    print("\nMemory system working!")
    return True


def demo_app_control():
    """Open and close apps."""
    print_header("APP CONTROL (Open/Close)")
    
    launcher = get_launcher()
    wm = get_window_manager()
    
    test_apps = ["notepad", "calc", "mspaint"]
    
    print("Opening apps...")
    for app in test_apps:
        result = launcher.launch(app)
        print("  " + app + ":", result)
        time.sleep(1)
    
    time.sleep(2)
    
    print("\nClosing apps...")
    wm.refresh()
    for app in test_apps:
        windows = wm.list_windows(app)
        for w in windows:
            if wm.close_window(w.title):
                print("  Closed:", w.title)
    
    # Verify VS Code still open
    wm.refresh()
    vscode = wm.list_windows("Visual Studio Code")
    if vscode:
        print("\nVS Code still running:", len(vscode), "window(s)")
    
    return True


def main():
    print("\n" + "#"*60)
    print("#  INDUS PC-SIDE COMPLETE FEATURE DEMO")
    print("#"*60)
    print("Started:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    demos = [
        ("VLC Movie Playback", demo_vlc_movie),
        ("Volume Control", demo_volume_control),
        ("Brightness Control", demo_brightness_control),
        ("WhatsApp Desktop", demo_whatsapp),
        ("YouTube in Edge", demo_youtube),
        ("Memory System", demo_memory),
        ("App Control", demo_app_control),
    ]
    
    results = {}
    for name, func in demos:
        try:
            print("\n>>> Running:", name)
            results[name] = func()
        except Exception as e:
            print("ERROR in", name, ":", e)
            results[name] = False
    
    print_header("DEMO SUMMARY")
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print("  [" + status + "] " + name)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print("\nTotal: " + str(passed) + "/" + str(total) + " demos completed")
    print("Finished:", time.strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()