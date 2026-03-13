param(
    [ValidateSet("start","stop","status")]
    [string]$Action = "start"
)

$ProjectRoot = "D:\utility-billing-ai"
$VenvActivate = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"
$UvicornExe   = Join-Path $ProjectRoot "venv\Scripts\uvicorn.exe"
$StreamlitExe = Join-Path $ProjectRoot "venv\Scripts\streamlit.exe"

$ApiPort = 8001
$UiPort  = 8501

function Start-Stack {
    Write-Host "Starting FastAPI on port $ApiPort ..."
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "& '$VenvActivate'; Set-Location '$ProjectRoot'; & '$UvicornExe' src.api.main:app --reload --host 127.0.0.1 --port $ApiPort"
    )

    Start-Sleep -Seconds 3

    Write-Host "Starting Streamlit on port $UiPort ..."
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "& '$VenvActivate'; Set-Location '$ProjectRoot'; `$env:API_BASE_URL='http://127.0.0.1:$ApiPort'; & '$StreamlitExe' run app/streamlit_app.py --server.address 127.0.0.1 --server.port $UiPort"
    )

    Write-Host "Stack launched."
    Write-Host "API: http://127.0.0.1:$ApiPort"
    Write-Host "UI : http://127.0.0.1:$UiPort"
}

function Stop-Stack {
    Write-Host "Stopping uvicorn and streamlit..."
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match "python|uvicorn|streamlit" -and
            $_.CommandLine -match "utility-billing-ai"
        } |
        ForEach-Object {
            try {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
                Write-Host "Stopped PID $($_.ProcessId)"
            } catch {
                Write-Host "Could not stop PID $($_.ProcessId)"
            }
        }
}

function Show-Status {
    $procs = Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match "python|uvicorn|streamlit" -and
            $_.CommandLine -match "utility-billing-ai"
        }

    if (-not $procs) {
        Write-Host "No local stack processes found."
        return
    }

    $procs | Select-Object ProcessId, Name, CommandLine | Format-List
}

switch ($Action) {
    "start"  { Start-Stack }
    "stop"   { Stop-Stack }
    "status" { Show-Status }
}