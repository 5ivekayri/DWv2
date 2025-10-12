# Dark Weather v2 🌦️

**Dark Weather v2** — вторая версия проекта [Dark Weather v1](https://github.com/5ivekayri/Weather-Web-App).

## ✨ Основные цели v2
- Перепроектирование архитектуры (паттерн **Bridge**, модульный монолит).
- Интеграция нескольких погодных API (Yandex Weather, Open-Meteо и др.).
- Поддержка собственной метеостанции на Arduino/ESP + **MQTT**.
- Собственный **Core Manager** (админка) для мониторинга сервисов и станций.
- Новый API эндпоинт: рекомендации по одежде через **OpenRouter (LLM)**.

## 🛠️ Технологический стек
- **Backend:** Python, Django, DRF, Celery
- **Frontend:** React (TypeScript)
- **База данных:** MySQL (ORM Django, легко заменить на PostgreSQL)
- **Кэш:** Redis
- **Сообщения:** MQTT (Mosquitto)
- **LLM:** OpenRouter
- **DevOps:** Docker Compose, Traefik/Caddy, GitHub Actions

## 🚀 Быстрый старт для разработки
1. Создайте и активируйте виртуальное окружение Python 3.12:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
2. Установите инструменты разработки:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Настройте `pre-commit` (один раз на машину):
   ```bash
   pre-commit install
   ```

## ✅ Проверка качества кода
- Линтеры и форматтеры (ruff, black, isort):
  ```bash
  ruff check .
  black --check .
  isort --check-only .
  ```
- Тесты:
  ```bash
  pytest
  ```

Эти же проверки запускает GitHub Actions в workflow [`ci.yml`](.github/workflows/ci.yml).

## 📚 Документация
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — описание архитектуры и ссылки на диаграммы.
- `docs/diagrams/` — исходники диаграмм (Mermaid/PlantUML и т.п.).

## 📂 Репозиторий
- `backend/` — Django API + Core Logic
- `frontend/` — React SPA
- `docs/` — документация (`ARCHITECTURE.md`, диаграммы Mermaid)
- `infra/` — скрипты, CI/CD, конфигурации

## 🚀 Запуск backend (dev)

### Подготовка окружения
1. Скопируйте `.env.example` в `.env` и заполните значения.
2. Установите Python 3.11+ и Poetry/virtualenv (по желанию).

### Локальный запуск
```bash
pip install django djangorestframework django-redis mysqlclient
export DJANGO_SETTINGS_MODULE=backend.settings
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### Docker Compose
```bash
docker compose up --build
```
Сервисы:
- `django` — приложение Django (`http://localhost:8000`)
- `redis` — кэш для погодных ответов
- `mysql` — основная база данных

### Тесты
```bash
pytest -q
```

После запуска `GET /api/weather?lat=55.75&lon=37.61` вернёт нормализованный JSON с фиктивными данными.
