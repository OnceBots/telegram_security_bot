from prometheus_client import Counter, Gauge, Histogram
CAPTCHA_STARTED = Counter("telegram_security_captcha_started_total", "CAPTCHA challenges created")
CAPTCHA_APPROVED = Counter("telegram_security_captcha_approved_total", "Join requests approved")
CAPTCHA_REJECTED = Counter("telegram_security_captcha_rejected_total", "Join requests rejected")
CAPTCHA_TIMEOUT = Counter("telegram_security_captcha_timeout_total", "Expired verifications")
HANDLER_ERRORS = Counter("telegram_security_handler_errors_total", "Unexpected errors")
ACTIVE_SESSIONS = Gauge("telegram_security_active_sessions", "Active sessions in this process")
VERIFICATION_DURATION = Histogram("telegram_security_verification_duration_seconds", "Verification duration", buckets=(1,5,10,30,60,120,300))
