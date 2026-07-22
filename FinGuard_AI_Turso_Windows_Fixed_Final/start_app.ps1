Set-Location $PSScriptRoot
$python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & $python -m venv .venv
}
$venvPython = ".venv\Scripts\python.exe"
$needsInstall = -not (Test-Path ".venv\requirements.lock")
if (-not $needsInstall) {
    $current = (Get-FileHash requirements.txt -Algorithm SHA256).Hash
    $locked = (Get-FileHash .venv\requirements.lock -Algorithm SHA256).Hash
    $needsInstall = $current -ne $locked
}
if ($needsInstall) {
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt
    Copy-Item requirements.txt .venv\requirements.lock -Force
}
& $venvPython scripts\preflight.py
Start-Process "http://127.0.0.1:8501"
& $venvPython -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
