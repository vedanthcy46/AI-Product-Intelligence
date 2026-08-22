# PaaS entrypoint (Render / Railway / Fly.io).
# Single process on purpose: live progress lives in an in-memory JOB dict and
# state in products.json — never scale beyond 1 instance/worker.
web: python -m waitress --host 0.0.0.0 --port ${PORT} frontend.server:app
