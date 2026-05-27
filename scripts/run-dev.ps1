$ErrorActionPreference = "Stop"

if (!(Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
