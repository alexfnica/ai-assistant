"""Windows-only helper: bring the Spotify desktop app to the front and type a search into its search bar.
Doing what a person would do also wakes the app, so that Spotify's own play command is then honoured."""
import base64
import subprocess

SCRIPT = r'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System; using System.Runtime.InteropServices;
public class SpW { [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c); [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h); }
"@
$q = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__Q__'))
$p = $null
for ($i = 0; $i -lt 10 -and -not $p; $i++) {
  $p = Get-Process Spotify -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
  if (-not $p) { Start-Sleep -Milliseconds 700 }
}
if (-not $p) { exit 2 }
if ([SpW]::IsIconic($p.MainWindowHandle)) { [SpW]::ShowWindow($p.MainWindowHandle, 9) | Out-Null }
[SpW]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 800
$old = $null; try { $old = Get-Clipboard -Raw } catch {}
Set-Clipboard -Value $q
[System.Windows.Forms.SendKeys]::SendWait('^l'); Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait('^a'); Start-Sleep -Milliseconds 150
[System.Windows.Forms.SendKeys]::SendWait('^v'); Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait('{ENTER}'); Start-Sleep -Milliseconds 900
if ($old) { Set-Clipboard -Value $old }
exit 0
'''


def command(query):
    """The PowerShell command line for a search (exposed for tests)."""
    q = base64.b64encode(query.encode("utf-8")).decode("ascii")
    encoded = base64.b64encode(SCRIPT.replace("__Q__", q).encode("utf-16-le")).decode("ascii")
    return ["powershell.exe", "-NoProfile", "-Sta", "-WindowStyle", "Hidden", "-EncodedCommand", encoded]


def search_in_app(query):
    """Focus Spotify and search for `query`. Returns True when the app window was found and the keys were sent."""
    try:
        return subprocess.run(command(query), timeout=25, capture_output=True).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
