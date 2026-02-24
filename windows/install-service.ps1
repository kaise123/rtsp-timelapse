# RTSP Timelapse - Windows Service Setup
#
# This script helps install the timelapse as a Windows service using NSSM
# (Non-Sucking Service Manager) or as a Task Scheduler task.
#
# Option 1: NSSM (recommended for true Windows Service)
# 1. Download NSSM from https://nssm.cc/download
# 2. Extract and add nssm.exe to your PATH, or use full path below
# 3. Run this script as Administrator
#
# Option 2: Task Scheduler (simpler, runs at login/startup)
# Use the commands at the end of this script to create a scheduled task.

$ErrorActionPreference = "Stop"

# --- Configuration: Edit these paths ---
$ProjectDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PythonExe = "python"  # or full path: "C:\Python311\python.exe"
$ConfigPath = Join-Path $ProjectDir "config.yaml"
$TimelapseScript = Join-Path $ProjectDir "timelapse.py"

# Verify paths exist
if (-not (Test-Path $TimelapseScript)) {
    Write-Error "Timelapse script not found: $TimelapseScript"
}
if (-not (Test-Path $ConfigPath)) {
    Write-Warning "Config not found: $ConfigPath - create from config.example.yaml"
}

# --- NSSM Service Installation ---
$ServiceName = "RTSPTimelapse"
$NssmPath = "nssm"  # or "C:\path\to\nssm.exe"

function Install-NssmService {
    Write-Host "Installing RTSP Timelapse as Windows Service via NSSM..."
    & $NssmPath install $ServiceName $PythonExe $TimelapseScript
    & $NssmPath set $ServiceName AppParameters "--config `"$ConfigPath`""
    & $NssmPath set $ServiceName AppDirectory $ProjectDir
    & $NssmPath set $ServiceName DisplayName "RTSP Timelapse"
    & $NssmPath set $ServiceName Description "Captures frames from RTSP camera at scheduled times for timelapse"
    Write-Host "Service installed. Start with: nssm start $ServiceName"
    Write-Host "Or: Start-Service $ServiceName"
}

# --- Task Scheduler (alternative) ---
function Install-TaskSchedulerTask {
    Write-Host "Creating Task Scheduler task to run at startup..."
    $TaskName = "RTSPTimelapse"
    $Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$TimelapseScript`" --config `"$ConfigPath`"" -WorkingDirectory $ProjectDir
    $Trigger = New-ScheduledTaskTrigger -AtStartup
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "RTSP Timelapse - Capture frames at scheduled times"
    Write-Host "Task created. Enable with: Enable-ScheduledTask -TaskName $TaskName"
}

# --- Main ---
Write-Host "RTSP Timelapse - Windows Service Setup"
Write-Host "Project: $ProjectDir"
Write-Host ""
Write-Host "Choose installation method:"
Write-Host "1) NSSM (Windows Service) - requires NSSM installed"
Write-Host "2) Task Scheduler (runs at startup)"
Write-Host "3) Exit"
$choice = Read-Host "Enter 1, 2, or 3"

switch ($choice) {
    "1" { Install-NssmService }
    "2" { Install-TaskSchedulerTask }
    "3" { Write-Host "Exiting." }
    default { Write-Host "Invalid choice." }
}
