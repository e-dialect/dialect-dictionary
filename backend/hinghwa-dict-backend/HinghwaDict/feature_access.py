"""Feature gating supplements, and never replaces, existing endpoint permissions."""
import os
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from utils.token import token_pass, token_user
from .feature_policy import capabilities, read_policy, permits


def policy_path():
    return getattr(settings, "FEATURE_POLICY_PATH", os.environ.get("FEATURE_POLICY_PATH", "/config/feature-policy.json"))


@require_GET
def public_capabilities(request):
    response = JsonResponse(capabilities(policy_path()))
    response["Cache-Control"] = "no-store, max-age=0"
    response["Pragma"] = "no-cache"
    return response


class WordApplicationPolicyMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.method.upper() not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            rule = read_policy(policy_path())
            if not rule or not rule["enabled"] or not rule["roles"]:
                return JsonResponse({"msg": "词条贡献当前未开放", "code": "feature_disabled"}, status=403)
            user = token_user(token_pass(request.headers, 0))
            if not permits(rule, user):
                return JsonResponse({"msg": "当前账号未获准使用词条贡献", "code": "feature_forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)
