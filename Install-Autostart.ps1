# Creates "A.I Assistant" shortcuts (own icon) in the Startup folder and on the Desktop.
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$shell = New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath('Startup'), [Environment]::GetFolderPath('Desktop'))) {
    $lnk = $shell.CreateShortcut((Join-Path $folder 'A.I Assistant.lnk'))
    $lnk.TargetPath = Join-Path $env:WINDIR 'System32\wscript.exe'
    $lnk.Arguments = '"' + (Join-Path $dir 'Jarvis-Silent.vbs') + '"'
    $lnk.WorkingDirectory = $dir
    $lnk.IconLocation = (Join-Path $dir 'assets\ai-assistant.ico')
    $lnk.Description = 'A.I Assistant'
    $lnk.Save()
}
Write-Host 'Done. A.I Assistant starts when you log in to Windows; a shortcut with its icon is on the Desktop.'
