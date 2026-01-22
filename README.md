# Учёт прохождения учебной страницы

Небольшое веб-приложение для генерации учебных приглашений и фиксации посещений.

## Возможности

- Админ-панель с логином и созданием приглашений.
- Страница сотрудника по ссылке `/t/{token}` с прозрачным сообщением о записи факта посещения.
- Статистика по всем приглашениям (всего и уникальные посещения).
- Журнал последних 100 событий (accepted/expired/disabled/invalid).

## Быстрый старт

1. Создайте файл окружения:

```bash
cp .env.example .env
```

2. Установите зависимости и запустите приложение:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Приложение будет доступно на `http://localhost:8000`.

### Docker

```bash
docker build -t training-invites .
docker run --env-file .env -p 8000:8000 training-invites
```

При желании используйте `docker-compose.yml`.

## Примеры запросов (curl)

### Логин в админку

```bash
curl -i -X POST http://localhost:8000/admin/login \
  -d "username=admin" -d "password=admin"
```

### Создание приглашения

```bash
curl -i -X POST http://localhost:8000/admin/invites \
  -H "Cookie: admin_session=<cookie>" \
  -d "note=Фишинг" -d "campaign=awareness"
```

### Переход по ссылке сотрудника

```bash
curl -i http://localhost:8000/t/<token>
```

## Переключение базы данных

По умолчанию используется SQLite (`sqlite:///./app.db`).
Чтобы переключиться на Postgres, задайте переменную окружения `DATABASE_URL`.

## Миграции

Для простоты таблицы создаются автоматически при старте приложения.
