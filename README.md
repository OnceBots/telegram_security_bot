# Telegram Security Bot v2

Sistema de verificación para solicitudes de ingreso a comunidades de Telegram.

## Qué cambia

- Arquitectura modular (`captcha`, `database`, `service`, `handlers`, `web`).
- PyMongo Async (`AsyncMongoClient`) en lugar de Motor.
- Sesiones consumidas de forma atómica para evitar carreras entre timeout y callback.
- TTL de MongoDB para sesiones y retención opcional de logs.
- CAPTCHA con `secrets`, respuestas aleatorias y dos intentos configurables.
- El callback solo puede ser utilizado por el usuario propietario de la sesión.
- Nombres y títulos escapados antes de insertarlos en HTML.
- Polling para desarrollo y webhook seguro para producción.
- `/health`, `/ready`, `/metrics`.
- Logging JSON.
- Docker, Compose, Render y GitHub Actions.
- Tests unitarios, Ruff y pip-audit.

## Inicio local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
python -m security_bot
```

Configura `BOT_TOKEN` y `MONGO_URI` en `.env`.

## Render

Usa `MODE=webhook`, una `WEBHOOK_BASE_URL` HTTPS apuntando al servicio y un `WEBHOOK_SECRET` aleatorio. El endpoint `/health` sirve de health check y `/webhook` recibe las actualizaciones de Telegram.

## Tests

```bash
pytest -q
ruff check .
pip-audit -r requirements.txt
```

## Estructura

```text
telegram_security_bot/
├── security_bot/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py
│   ├── config.py
│   ├── captcha.py
│   ├── database.py
│   ├── handlers.py
│   ├── logging_setup.py
│   ├── metrics.py
│   ├── rate_limit.py
│   ├── service.py
│   └── web.py
├── locales/es.json
├── locales/en.json
├── tests/test_captcha.py
├── tests/test_locales.py
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── requirements.txt
└── requirements-dev.txt
```
