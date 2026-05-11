from __future__ import annotations

import base64
import dataclasses
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import httpx
from openai import OpenAI


CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
CODEX_MODELS_URL = f"{CODEX_BASE_URL}/models?client_version=1.0.0"
CODEX_OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
CODEX_OAUTH_TOKEN_URL = "https://auth.openai.com/oauth/token"
DEFAULT_CODEX_MODEL = "gpt-5.5"


class OAuthProbeError(RuntimeError):
    pass


@dataclasses.dataclass
class TokenSource:
    name: str
    path: Path
    access_token: Optional[str]
    refresh_token: Optional[str]
    last_refresh: Optional[str] = None
    active_provider: Optional[str] = None

    @property
    def has_access_token(self) -> bool:
        return bool(self.access_token and self.access_token.strip())

    @property
    def has_refresh_token(self) -> bool:
        return bool(self.refresh_token and self.refresh_token.strip())


def _home() -> Path:
    return Path.home()


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except Exception as exc:
        raise OAuthProbeError(f"Could not parse {path}: {exc}") from exc


def load_hermes_codex_source() -> TokenSource:
    path = _home() / ".hermes" / "auth.json"
    payload = _load_json(path)
    provider = ((payload.get("providers") or {}).get("openai-codex") or {})
    tokens = provider.get("tokens") or {}
    return TokenSource(
        name="hermes-openai-codex",
        path=path,
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        last_refresh=provider.get("last_refresh"),
        active_provider=payload.get("active_provider"),
    )


def load_codex_cli_source() -> TokenSource:
    codex_home = Path(os.environ.get("CODEX_HOME", "")).expanduser()
    if not str(codex_home).strip() or str(codex_home) == ".":
        codex_home = _home() / ".codex"
    path = codex_home / "auth.json"
    payload = _load_json(path)
    tokens = payload.get("tokens") or {}
    return TokenSource(
        name="codex-cli",
        path=path,
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        last_refresh=payload.get("last_refresh"),
    )


def load_sources() -> list[TokenSource]:
    return [load_hermes_codex_source(), load_codex_cli_source()]


def decode_jwt_claims(token: Optional[str]) -> Dict[str, Any]:
    if not token or token.count(".") < 2:
        return {}
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
    except Exception:
        return {}


def token_metadata(source: TokenSource) -> Dict[str, Any]:
    claims = decode_jwt_claims(source.access_token)
    auth_claim = claims.get("https://api.openai.com/auth") or {}
    exp = claims.get("exp")
    now = int(time.time())
    return {
        "source": source.name,
        "path": str(source.path),
        "exists": source.path.exists(),
        "active_provider": source.active_provider,
        "last_refresh": source.last_refresh,
        "has_access_token": source.has_access_token,
        "has_refresh_token": source.has_refresh_token,
        "access_token_exp": exp,
        "access_token_exp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(exp)) if exp else None,
        "access_token_seconds_remaining": int(exp - now) if isinstance(exp, int) else None,
        "has_chatgpt_account_id_claim": bool(auth_claim.get("chatgpt_account_id")),
        "token_prefix": "redacted",
    }


def access_token_seconds_remaining(source: TokenSource) -> Optional[int]:
    claims = decode_jwt_claims(source.access_token)
    exp = claims.get("exp")
    if not isinstance(exp, int):
        return None
    return int(exp - time.time())


def refresh_access_token_in_memory(source: TokenSource) -> TokenSource:
    """Refresh a Codex OAuth access token without writing token material to disk."""
    if not source.has_refresh_token:
        raise OAuthProbeError(f"{source.name} has no refresh token.")
    response = httpx.post(
        CODEX_OAUTH_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": source.refresh_token,
            "client_id": CODEX_OAUTH_CLIENT_ID,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=httpx.Timeout(30.0),
    )
    if response.status_code != 200:
        raise OAuthProbeError(f"OAuth refresh failed with HTTP {response.status_code}")
    payload = response.json()
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token") or source.refresh_token
    if not isinstance(access_token, str) or not access_token:
        raise OAuthProbeError("OAuth refresh response did not contain an access token.")
    return dataclasses.replace(
        source,
        access_token=access_token,
        refresh_token=refresh_token if isinstance(refresh_token, str) else source.refresh_token,
        last_refresh=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


def ensure_fresh_access_token(source: TokenSource, *, min_seconds: int = 300) -> TokenSource:
    remaining = access_token_seconds_remaining(source)
    if remaining is None or remaining > min_seconds:
        return source
    return refresh_access_token_in_memory(source)


def choose_runtime_source(sources: Optional[Iterable[TokenSource]] = None) -> TokenSource:
    candidates = list(sources or load_sources())
    refresh_errors: list[str] = []
    for item in candidates:
        if item.name == "hermes-openai-codex" and item.has_access_token:
            try:
                return ensure_fresh_access_token(item)
            except OAuthProbeError as exc:
                refresh_errors.append(f"{item.name}: {exc}")
    for item in candidates:
        if item.has_access_token:
            try:
                return ensure_fresh_access_token(item)
            except OAuthProbeError as exc:
                refresh_errors.append(f"{item.name}: {exc}")
    suffix = f" Refresh failures: {'; '.join(refresh_errors)}" if refresh_errors else ""
    raise OAuthProbeError(f"No usable Codex/ChatGPT OAuth access token found.{suffix}")


def codex_headers(access_token: str) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "codex_cli_rs/0.0.0 (chatgpt-oauth-bridge)",
        "originator": "codex_cli_rs",
    }
    claims = decode_jwt_claims(access_token)
    auth_claim = claims.get("https://api.openai.com/auth") or {}
    account_id = auth_claim.get("chatgpt_account_id")
    if isinstance(account_id, str) and account_id:
        headers["ChatGPT-Account-ID"] = account_id
    return headers


def redacted_headers_for_report(headers: Dict[str, str]) -> Dict[str, str]:
    out = dict(headers)
    if "Authorization" in out:
        out["Authorization"] = "Bearer <redacted>"
    if "ChatGPT-Account-ID" in out:
        out["ChatGPT-Account-ID"] = "<redacted-present>"
    return out


def codex_http_client(access_token: str, timeout_seconds: float = 60.0) -> httpx.Client:
    return httpx.Client(
        headers=codex_headers(access_token),
        timeout=httpx.Timeout(timeout_seconds),
    )


def codex_openai_client(access_token: str) -> OpenAI:
    return OpenAI(
        api_key=access_token,
        base_url=CODEX_BASE_URL,
        default_headers={k: v for k, v in codex_headers(access_token).items() if k != "Authorization"},
    )


def fetch_codex_models(access_token: str) -> list[str]:
    with codex_http_client(access_token, timeout_seconds=30.0) as client:
        response = client.get(CODEX_MODELS_URL)
    if response.status_code != 200:
        raise OAuthProbeError(f"Codex models probe failed with HTTP {response.status_code}")
    payload = response.json()
    models = payload.get("models")
    if not isinstance(models, list):
        return []
    ids: list[str] = []
    for item in models:
        if isinstance(item, dict):
            model_id = item.get("id") or item.get("slug") or item.get("model")
            if isinstance(model_id, str):
                ids.append(model_id)
        elif isinstance(item, str):
            ids.append(item)
    return ids


def choose_text_model(model_ids: list[str]) -> str:
    return DEFAULT_CODEX_MODEL


def choose_image_host_model(model_ids: list[str]) -> str:
    return DEFAULT_CODEX_MODEL
