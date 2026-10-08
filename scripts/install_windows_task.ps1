# Registers "PersonalRadio" to start at logon, hidden, restarting on failure.
# Run once from the project folder in PowerShell:  .\scripts\install_windows_task.ps1
# Prereq: python -m venv .venv ; .\.venv\Scripts\pip install -r requirements.txt
#         then run `.\.venv\Scripts\python -m radio track` once by hand to log in to Spotify.
$dir = Split-Path $PSScriptRoot -Parent   # the project folder (this script lives in scripts/)
$py  = Join-Path $dir ".venv\Scripts\pythonw.exe"   # pythonw = no console window
$action   = New-ScheduledTaskAction -Execute $py -Argument "-m radio track" -WorkingDirectory $dir
$trigger  = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT30S"                            # let the network come up
$settings = New-ScheduledTaskSettingsSet -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1) `
            -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
            -StartWhenAvailable
Register-ScheduledTask -TaskName "PersonalRadio" -Action $action -Trigger $trigger -Settings $settings -Force
Write-Host "Installed. Logs: $dir\data\radio.log   Remove with: Unregister-ScheduledTask PersonalRadio"
