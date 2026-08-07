import subprocess
# Change app theme to dark
result = subprocess.run(['powershell', '-Command', 'Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" -Name "AppsUseLightTheme" -Value 0 -Type DWord'], capture_output=True, text=True)
print("Apps theme:", result.returncode)

# Change system theme to dark
result = subprocess.run(['powershell', '-Command', 'Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" -Name "SystemUsesLightTheme" -Value 0 -Type DWord'], capture_output=True, text=True)
print("System theme:", result.returncode)

# Restart explorer to apply
result = subprocess.run(['powershell', '-Command', 'Stop-Process -Name explorer -Force; Start-Process explorer'], capture_output=True, text=True)
print("Explorer restart:", result.returncode)