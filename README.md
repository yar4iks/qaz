# Visitor Tracker (Minimal)

## Что делает приложение

- Отдаёт одну страницу с текстом `Hello, guest<ip>`.
- Автоматически фиксирует IP посетителя в SQLite базе.
- Есть админская зона с базовой авторизацией.
- Есть сервис генерации ссылок, которые ведут на эту же страницу.
- Посещения админа не учитываются (по Basic Auth и/или по списку `ADMIN_IPS`).

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

По умолчанию приложение стартует на `http://localhost:5000`.

## Конфигурация

Создайте `.env` (пример в `.env.example`) и задайте переменные:

- `ADMIN_USER` и `ADMIN_PASSWORD` — логин/пароль админа.
- `ADMIN_IPS` — список IP админа через запятую (опционально).
- `VISITOR_DB_PATH` — путь к SQLite базе.
- `PORT` — порт сервера.

## Админские эндпоинты

- `GET /admin` — дашборд (Basic Auth).
- `POST /admin/generate` — генерация ссылки (Basic Auth).
- `GET /admin/visitors` — JSON список посетителей (Basic Auth).

## Генерация ссылок

Через админскую панель нажмите кнопку **Generate new link** или отправьте POST:

```bash
curl -u admin:password -X POST http://localhost:5000/admin/generate
```

Ответ:

```json
{"link": "http://localhost:5000/<token>"}
```
