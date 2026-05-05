param(
  [int]$Port = 8098
)

$env:PYTHONPATH = "src"
python -m uvicorn demotest.app.main:app --host 0.0.0.0 --port $Port --reload

