"""
Shutdown PC using Windows shutdown command.
Run: python shutdown_pc.py
"""

import sys
import subprocess
sys.path.insert(0, r'D:\Ansh Kesharwani\Documents\indus-phase1\indus')


def shutdown_pc(force: bool = False, delay: int = 0):
    """Shutdown the PC."""
    try:
        cmd = ["shutdown", "/s"]
        if force:
            cmd.append("/f")
        if delay > 0:
            cmd.extend(["/t", str(delay)])
        else:
            cmd.extend(["/t", "0"])
        
        print("Shutting down PC...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Shutdown initiated successfully.")
        else:
            print("Failed to shutdown: " + result.stderr)
            
    except Exception as e:
        print("Error: " + str(e))


def restart_pc(force: bool = False, delay: int = 0):
    """Restart the PC."""
    try:
        cmd = ["shutdown", "/r"]
        if force:
            cmd.append("/f")
        if delay > 0:
            cmd.extend(["/t", str(delay)])
        else:
            cmd.extend(["/t", "0"])
        
        print("Restarting PC...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Restart initiated successfully.")
        else:
            print("Failed to restart: " + result.stderr)
            
    except Exception as e:
        print("Error: " + str(e))


def cancel_shutdown():
    """Cancel a pending shutdown."""
    try:
        cmd = ["shutdown", "/a"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Shutdown cancelled.")
        else:
            print("No shutdown to cancel or failed: " + result.stderr)
            
    except Exception as e:
        print("Error: " + str(e))


def main():
    import sys
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        if action == "restart":
            restart_pc(force=True, delay=0)
        elif action == "cancel":
            cancel_shutdown()
        else:
            shutdown_pc(force=True, delay=0)
    else:
        print("Shutting down PC in 5 seconds... (Ctrl+C to cancel)")
        import time
        time.sleep(5)
        shutdown_pc(force=True, delay=0)


if __name__ == "__main__":
    main()