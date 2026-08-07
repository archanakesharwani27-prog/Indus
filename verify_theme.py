import subprocess
# Verify current theme settings
result = subprocess.run(['powershell', '-Command', 'Get-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" -Name "AppsUseLightTheme", "SystemUsesLightTheme"'], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)