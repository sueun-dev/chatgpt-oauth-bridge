from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from classify_openai_path import normalize_path


ENABLE_ENV = "OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK"
MODE_ENV = "OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE"
BASE_URL_ENV = "OAUTH_BRIDGE_PLATFORM_BASE_URL"
API_KEY_ENV = "OPENAI_API_KEY"
ADMIN_KEY_ENV = "OPENAI_ADMIN_KEY"
ACCESS_TOKEN_ENV = "OPENAI_ACCESS_TOKEN"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODE = "boundary"
PLACEHOLDER_CREDENTIALS = {"oauth-local-proxy"}

FALLBACK_ELIGIBLE_CATEGORIES = {
    "api_key_or_admin_key_required",
    "resource_bound_not_fully_verified",
    "official_route_auth_reached_but_not_complete",
    "not_available_current_deployment",
    "not_probed_directly",
}

PREFER_PLATFORM_CATEGORIES = {
    "direct_official_oauth_verified",
    "local_compat_or_chatgpt_backend_bridge",
    *FALLBACK_ELIGIBLE_CATEGORIES,
}


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def is_admin_surface(path: str) -> bool:
    normalized = normalize_path(path)
    return normalized.startswith("/organization/") or normalized.startswith("/projects/")


def credential_envs_for_path(path: str) -> list[str]:
    if is_admin_surface(path):
        return [ADMIN_KEY_ENV]
    return [API_KEY_ENV, ACCESS_TOKEN_ENV]


def credential_env_for_path(path: str) -> str:
    return credential_envs_for_path(path)[0]


def platform_base_url() -> str:
    return os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL).rstrip("/")


def platform_fallback_mode() -> str:
    mode = os.environ.get(MODE_ENV, DEFAULT_MODE).strip().lower()
    if mode in {"prefer", "prefer_platform", "platform"}:
        return "prefer"
    return DEFAULT_MODE


def platform_fallback_enabled() -> bool:
    return truthy(os.environ.get(ENABLE_ENV))


def credential_for_path(path: str) -> Tuple[str, str]:
    env_names = credential_envs_for_path(path)
    for env_name in env_names:
        token = os.environ.get(env_name, "")
        if token and token.strip() not in PLACEHOLDER_CREDENTIALS:
            return token, env_name
    return "", env_names[0]


def credential_env_present(env_name: str) -> bool:
    token = os.environ.get(env_name, "")
    return bool(token and token.strip() not in PLACEHOLDER_CREDENTIALS)


def path_fallback_state(path: str, category: str | None = None, *, prefer_platform: bool = False) -> Dict[str, Any]:
    token, env_name = credential_for_path(path)
    mode = platform_fallback_mode()
    eligible = category in FALLBACK_ELIGIBLE_CATEGORIES if category else True
    prefer = prefer_platform or mode == "prefer"
    if prefer and category:
        eligible = category in PREFER_PLATFORM_CATEGORIES
    enabled = platform_fallback_enabled()
    return {
        "enabled": enabled,
        "mode": mode,
        "prefer_platform": prefer,
        "eligible": eligible,
        "base_url": platform_base_url(),
        "credential_env": env_name,
        "credential_envs": credential_envs_for_path(path),
        "credential_present": bool(token),
        "admin_surface": is_admin_surface(path),
        "can_forward": enabled and eligible and bool(token),
    }


def global_fallback_state() -> Dict[str, Any]:
    return {
        "enabled": platform_fallback_enabled(),
        "mode": platform_fallback_mode(),
        "enable_env": ENABLE_ENV,
        "mode_env": MODE_ENV,
        "base_url_env": BASE_URL_ENV,
        "base_url": platform_base_url(),
        "api_key_env": API_KEY_ENV,
        "api_key_present": credential_env_present(API_KEY_ENV),
        "admin_key_env": ADMIN_KEY_ENV,
        "admin_key_present": credential_env_present(ADMIN_KEY_ENV),
        "access_token_env": ACCESS_TOKEN_ENV,
        "access_token_present": credential_env_present(ACCESS_TOKEN_ENV),
        "default_behavior": "disabled; known boundary paths return structured oauth_compat.boundary responses",
        "modes": {
            "boundary": "Forward only known boundary paths when fallback is enabled and a matching credential is present.",
            "prefer": "Forward official OpenAI paths before local compatibility handlers when fallback is enabled and a matching credential is present.",
        },
    }
