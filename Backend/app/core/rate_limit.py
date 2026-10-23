from fastapi import Request
from slowapi import Limiter
from app.core.config import settings

def get_trusted_client_ip(request: Request) -> str:
    """
    Safely resolves client IP. Only inspects forwarded headers (CF-Connecting-IP,
    X-Forwarded-For) if TRUST_PROXY_HEADERS is explicitly True or if the immediate
    socket connection is from a configured TRUSTED_PROXIES host (e.g. 127.0.0.1).
    This strictly prevents rate-limiting and access-logging spoofing by untrusted clients.
    """
    immediate_ip = request.client.host if request.client else ""
    is_trusted = (
        getattr(settings, "TRUST_PROXY_HEADERS", False) or
        "*" in getattr(settings, "TRUSTED_PROXIES", []) or
        immediate_ip in getattr(settings, "TRUSTED_PROXIES", [])
    )
    if is_trusted:
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip and cf_ip.strip():
            return cf_ip.strip()
        xff = request.headers.get("x-forwarded-for")
        if xff and xff.strip():
            # First element is the client IP before upstream proxies
            return xff.split(",")[0].strip()
    return immediate_ip

# Default limiter with safe trusted-proxy client IP key function
limiter = Limiter(
    key_func=get_trusted_client_ip,
    default_limits=["120/minute"],
    storage_uri="memory://"
)
