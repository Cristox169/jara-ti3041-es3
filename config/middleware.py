from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone


class InactivityLogoutMiddleware:
    """Cierra la sesión tras siete minutos sin una solicitud autenticada."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        login_paths = {settings.LOGIN_URL, settings.LOGIN_URL.rstrip("/") + "/"}
        public_path = (
            request.path in login_paths
            or request.path.startswith("/admin/")
            or request.path.startswith("/static/")
        )
        if not public_path and (user is None or not user.is_authenticated):
            return redirect(f"{settings.LOGIN_URL}?next={quote(request.get_full_path())}")
        if not public_path and user is not None and user.is_authenticated:
            now = timezone.now().timestamp()
            last_activity = request.session.get("crissteel_last_activity")
            timeout = getattr(settings, "SESSION_INACTIVITY_TIMEOUT", 420)
            if last_activity and now - float(last_activity) >= timeout:
                logout(request)
                next_url = quote(request.get_full_path())
                return redirect(f"{settings.LOGIN_URL}?expired=1&next={next_url}")
            request.session["crissteel_last_activity"] = now
            request.session.modified = True
        return self.get_response(request)
