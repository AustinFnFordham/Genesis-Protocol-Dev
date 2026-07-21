# Genesis UI v0.1 — local QA server
# Rebuilds campaign_data.json from Gold/WIP, then serves the UI.
Set-Location $PSScriptRoot
python build_data.py
Start-Process "http://localhost:8777"
python -m http.server 8777
