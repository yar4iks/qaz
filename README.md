# Minimal visitor tracker

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

По умолчанию админ логин/пароль: `admin` / `admin`.

Можно переопределить через переменные окружения:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SECRET_KEY`
- `VISITOR_DB` (путь к SQLite базе)
