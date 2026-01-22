# Учёт посещений учебной страницы

Простое веб-приложение для фиксации посещений учебной страницы по информационной безопасности.

## Возможности

- Админ-панель для создания приглашений.
- Журнал последних посещений и статистика по токенам.
- Серверный рендеринг через Jinja2.
- SQLite по умолчанию, переключение на Postgres через `DATABASE_URL`.

## Быстрый старт (локально)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Админ-панель доступна по адресу: `http://localhost:8000/admin`.

## Запуск через Docker

```bash
cp .env.example .env
docker compose up --build
```

## Переменные окружения

- `DATABASE_URL` — строка подключения (например, `sqlite:///./app.db` или `postgresql+psycopg://...`).
- `ADMIN_USER` / `ADMIN_PASSWORD` — учётные данные администратора.
- `SECRET_KEY` — ключ для подписи cookie-сессии.

## Примеры запросов (curl)

Создание приглашения (нужна cookie сессии администратора):

```bash
curl -i -X POST http://localhost:8000/admin/invites \
  -H "Cookie: admin_session=<token>" \
  -F "note=Test" \
  -F "campaign=Onboarding"
```

Проверка трекинга:

```bash
curl -i http://localhost:8000/t/<token>
```

## Примечания

- Таблицы создаются автоматически при старте приложения.
- Для Postgres укажите `DATABASE_URL` и установите соответствующий драйвер.
