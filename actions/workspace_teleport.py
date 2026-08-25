# actions/workspace_teleport.py
# INDUS Workspace Teleportation & Window Snapping
import subprocess, sys

def _ps(script: str) -> str:
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip() or "Done."
    except Exception as e:
        return f"Snap error: {e}"

def _kb_snap(direction: str) -> str:
    import pyautogui
    pyautogui.FAILSAFE = False
    combos = {"left": ["win","left"], "right": ["win","right"],
              "maximize": ["win","up"], "minimize": ["win","down"]}
    keys = combos.get(direction, [])
    if keys: pyautogui.hotkey(*keys)
    return f"Window snapped {direction}."

def teleport_workspace(layout: str = "split_dev", player=None) -> str:
    """Organize desktop windows into named layouts."""
    layout = layout.lower().strip()
    if player: player.write_log(f"[Workspace] Layout: {layout}")

    if layout in ("focus", "maximize"):
        return _kb_snap("maximize")
    if layout == "split_left":
        return _kb_snap("left")
    if layout == "split_right":
        return _kb_snap("right")
    if layout == "split_dev":
        script = (
            '$sw=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width;'
            '$sh=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height;'
            '$h=$sw/2;'
            'Add-Type -AssemblyName System.Windows.Forms;'
            'Add-Type -TypeDefinition "using System.Runtime.InteropServices;public class W32{[DllImport(\\"user32.dll\\")]public static extern bool MoveWindow(System.IntPtr h,int x,int y,int w,int ht,bool r);}";'
            '$vc=Get-Process|Where-Object{$_.ProcessName -eq "Code" -or $_.MainWindowTitle -like "*Visual Studio Code*"}|Select-Object -First 1;'
            '$br=Get-Process|Where-Object{$_.ProcessName -in "chrome","msedge","opera","firefox"}|Select-Object -First 1;'
            'if($vc){[W32]::MoveWindow($vc.MainWindowHandle,0,0,$h,$sh,$true)};'
            'if($br){[W32]::MoveWindow($br.MainWindowHandle,$h,0,$h,$sh,$true)}'
        )
        _ps(script)
        return "Dev layout set: VS Code (left 50%) + Browser (right 50%)."
    if layout == "quad":
        import pyautogui
        sw, sh = pyautogui.size()
        hw, hh = sw//2, sh//2
        script = (
            f'Add-Type -TypeDefinition "using System.Runtime.InteropServices;public class W32{{[DllImport(\\"user32.dll\\")]public static extern bool MoveWindow(System.IntPtr h,int x,int y,int w,int ht,bool r);}}";'
            f'$wins=Get-Process|Where-Object{{$_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -ne ""}}|Select-Object -First 4;'
            f'$pos=@(@(0,0),@(1,0),@(0,1),@(1,1));'
            f'for($i=0;$i -lt $wins.Count;$i++){{$p=$pos[$i];[W32]::MoveWindow($wins[$i].MainWindowHandle,$p[0]*{hw},$p[1]*{hh},{hw},{hh},$true)}}'
        )
        _ps(script)
        return "Quad layout applied: 4 windows in 2x2 grid."
    return f"Unknown layout: {layout}. Available: split_dev | focus | quad | split_left | split_right"
