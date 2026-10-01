from dataclasses import dataclass
import os

def _int_env(name: str, default: int, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    value = default if raw in (None, "") else int(raw)
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value

@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    mongo_uri: str = os.getenv("MONGO_URI", "")
    db_name: str = os.getenv("DB_NAME", "security_bot")
    mode: str = os.getenv("MODE", "polling").lower()
    port: int = _int_env("PORT", 8080, 1)
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    drop_pending_updates: bool = os.getenv("DROP_PENDING_UPDATES", "true").lower() == "true"
    captcha_timeout: int = _int_env("CAPTCHA_TIMEOUT", 120, 1)
    captcha_max_attempts: int = _int_env("CAPTCHA_MAX_ATTEMPTS", 2, 1)
    captcha_min_a: int = _int_env("CAPTCHA_MIN_A", 2, 0)
    captcha_max_a: int = _int_env("CAPTCHA_MAX_A", 15, 0)
    captcha_min_b: int = _int_env("CAPTCHA_MIN_B", 1, 0)
    captcha_max_b: int = _int_env("CAPTCHA_MAX_B", 14, 0)
    join_rate_limit: int = _int_env("JOIN_RATE_LIMIT", 5, 1)
    join_rate_window_seconds: int = _int_env("JOIN_RATE_WINDOW_SECONDS", 60, 1)
    webhook_base_url: str = os.getenv("WEBHOOK_BASE_URL", "").rstrip("/")
    webhook_path: str = os.getenv("WEBHOOK_PATH", "/webhook")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")
    mongo_server_selection_timeout_ms: int = _int_env("MONGO_SERVER_SELECTION_TIMEOUT_MS", 5000, 100)
    mongo_connect_timeout_ms: int = _int_env("MONGO_CONNECT_TIMEOUT_MS", 10000, 100)
    mongo_socket_timeout_ms: int = _int_env("MONGO_SOCKET_TIMEOUT_MS", 10000, 100)
    access_log_ttl_days: int = _int_env("ACCESS_LOG_TTL_DAYS", 90, 0)

    def validate(self) -> None:
        if not self.bot_token:
            raise ValueError("BOT_TOKEN no está configurado.")
        if not self.mongo_uri:
            raise ValueError("MONGO_URI no está configurado.")
        if self.mode not in {"polling", "webhook"}:
            raise ValueError("MODE debe ser 'polling' o 'webhook'.")
        if not self.webhook_path.startswith("/"):
            raise ValueError("WEBHOOK_PATH debe comenzar con '/'.")
        if self.captcha_min_a > self.captcha_max_a or self.captcha_min_b > self.captcha_max_b:
            raise ValueError("Rango CAPTCHA inválido.")
        if self.mode == "webhook":
            if not self.webhook_base_url.startswith("https://"):
                raise ValueError("WEBHOOK_BASE_URL debe ser HTTPS en modo webhook.")
            if not (1 <= len(self.webhook_secret) <= 256):
                raise ValueError("WEBHOOK_SECRET debe tener entre 1 y 256 caracteres.")
