from celery import Celery

from app.config import settings

# Upstash Redis requires rediss:// (TLS). We need to pass SSL options.
_redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
_is_tls = _redis_url.startswith("rediss://")

celery_app = Celery(
    "document_intelligence",
    broker=_redis_url,
    backend=_redis_url,
    include=["app.tasks.document_tasks"],
)

# SSL config required for Upstash (rediss://) connections
_broker_transport_options = {}
_redis_backend_health_check_interval = None
if _is_tls:
    import ssl
    _ssl_config = {"ssl_cert_reqs": ssl.CERT_NONE}
    _broker_transport_options = {"ssl": _ssl_config}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    broker_transport_options=_broker_transport_options,
    redis_backend_use_ssl=_ssl_config if _is_tls else None,
)
