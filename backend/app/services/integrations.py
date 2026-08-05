"""Tenant-isolated integration secrets and outbound provider clients."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import tenant_session

if TYPE_CHECKING:
    from app.api.deps import ActorContext

SUPPORTED_PROVIDERS = frozenset({"deepseek", "vision", "voice", "tavily"})
DEEPSEEK_RUNTIME_MODELS = {
    "balanced": "deepseek-v4-flash",
    "thinking": "deepseek-v4-pro",
}
DEFAULTS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": DEEPSEEK_RUNTIME_MODELS["thinking"],
    },
    "tavily": {"base_url": "https://api.tavily.com", "model": "tavily-search"},
    "vision": {"base_url": "", "model": "auto"},
    "voice": {
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "auto",
        "asr_model": "FunAudioLLM/SenseVoiceSmall",
        "tts_model": "FunAudioLLM/CosyVoice2-0.5B",
        "tts_voice": "FunAudioLLM/CosyVoice2-0.5B:anna",
    },
}

VOICE_MAX_AUDIO_BYTES = 8 * 1024 * 1024
VOICE_MAX_SPEECH_CHARS = 560
VOICE_MAX_SPEECH_BYTES = 12 * 1024 * 1024
VOICE_CATALOG_CACHE_SECONDS = 300.0
VOICE_CATALOG_FAILURE_CACHE_SECONDS = 30.0
VOICE_AUDIO_TYPES = {
    "audio/webm": "webm",
    "video/webm": "webm",
    "audio/mp4": "mp4",
    "video/mp4": "mp4",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/ogg": "ogg",
    "audio/opus": "opus",
    "audio/x-m4a": "m4a",
}
_VOICE_CATALOG_CACHE: dict[
    str, tuple[float, frozenset[str] | None, str]
] = {}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    latency_ms: int
    error: str | None = None


@dataclass(frozen=True)
class ModelConnection:
    """A tenant-scoped model connection for the shared Auto Runtime only."""

    base_url: str
    model: str
    api_key: str


@dataclass(frozen=True)
class VoiceTranscription:
    text: str
    model: str
    trace_id: str | None


@dataclass(frozen=True)
class VoiceSpeech:
    audio: bytes
    content_type: str
    model: str
    trace_id: str | None


@dataclass(frozen=True)
class VoiceRuntime:
    base_url: str
    api_key: str
    asr_model: str
    tts_model: str
    tts_voice: str
    vendor: str


class VoiceIntegrationError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def chat_completion(
    connection: ModelConnection,
    *,
    system_prompt: str,
    user_prompt: str,
    timeout: float = 60.0,
    thinking: bool | None = None,
    max_tokens: int | None = None,
    json_mode: bool = False,
) -> str:
    """Use the tenant-scoped model connection through one shared boundary."""
    request: dict[str, object] = {
        "model": connection.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if thinking is not None:
        request["thinking"] = {
            "type": "enabled" if thinking else "disabled",
        }
    if max_tokens is not None:
        request["max_tokens"] = max_tokens
    if json_mode:
        request["response_format"] = {"type": "json_object"}
    response = httpx.post(
        f"{connection.base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {connection.api_key}",
            "Content-Type": "application/json",
        },
        json=request,
        timeout=timeout,
    )
    response.raise_for_status()
    try:
        message = response.json()["choices"][0]["message"].get("content")
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("AI provider returned an invalid response") from exc
    if not isinstance(message, str) or not message.strip():
        raise ValueError("AI provider returned an empty response")
    return message.strip()


def normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise ValueError("Unsupported integration provider")
    return normalized


def _fernet(settings: Settings) -> Fernet:
    digest = hashlib.sha256(settings.integration_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(secret: str, settings: Settings) -> str:
    return "fernet:v1:" + _fernet(settings).encrypt(secret.encode("utf-8")).decode("ascii")


def _decrypt(payload: dict[str, object], settings: Settings) -> str:
    encrypted = str(payload.get("secret_ciphertext") or "")
    if encrypted.startswith("fernet:v1:"):
        try:
            return _fernet(settings).decrypt(encrypted.removeprefix("fernet:v1:").encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Integration credential cannot be decrypted") from exc
    # One-way compatibility for credentials written by the former plaintext route.
    return str(payload.get("api_key") or "")


def _stored(actor: ActorContext, provider: str) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        value = session.execute(
            text(
                """
                SELECT payload FROM compatibility.documents
                WHERE namespace = :namespace AND document_key = 'default' AND status = 'active'
                """
            ),
            {"namespace": f"integration.{provider}"},
        ).scalar_one_or_none()
    return dict(value) if isinstance(value, dict) else {}


def _write(actor: ActorContext, provider: str, payload: dict[str, object]) -> None:
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO compatibility.documents(
                  id, tenant_id, namespace, document_key, payload, source, updated_by
                ) VALUES (
                  :id, :tenant_id, :namespace, 'default', CAST(:payload AS jsonb),
                  'native', :updated_by
                )
                ON CONFLICT (tenant_id, namespace, document_key)
                DO UPDATE SET payload = EXCLUDED.payload, status = 'active',
                  source = EXCLUDED.source, version = compatibility.documents.version + 1,
                  updated_by = EXCLUDED.updated_by
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "namespace": f"integration.{provider}",
                "payload": json.dumps(payload, ensure_ascii=False),
                "updated_by": actor.user_id,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (:tenant_id, :actor_user_id, 'integration.configuration.updated',
                        CAST(:payload AS jsonb))
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": json.dumps(
                    {"provider": provider, "configured": bool(payload.get("secret_ciphertext"))}
                ),
            },
        )


def public_state(actor: ActorContext, provider: str) -> dict[str, object]:
    provider = normalize_provider(provider)
    stored = _stored(actor, provider)
    configured = bool(stored.get("secret_ciphertext") or stored.get("api_key"))
    connection_status = str(
        stored.get("connection_status")
        or ("pending_validation" if configured else "not_configured")
    )
    connected = configured and connection_status == "connected"
    connection = {
        "ok": connected,
        "status": connection_status,
        "model": stored.get("model") or DEFAULTS[provider]["model"],
        "checked_at": stored.get("checked_at") or stored.get("updated_at"),
        "error": stored.get("last_error"),
    }
    base_url = stored.get("base_url") or DEFAULTS[provider]["base_url"]
    state: dict[str, object] = {
        "provider": provider,
        "configured": configured,
        "connected": connected,
        "connection_status": connection_status,
        "masked_key": stored.get("key_hint") or ("••••" if configured else "—"),
        "model": stored.get("model") or DEFAULTS[provider]["model"],
        "base_url": base_url,
        "updated_at": stored.get("updated_at"),
        "connection": connection,
    }
    if provider == "deepseek":
        state["runtime_models"] = dict(DEEPSEEK_RUNTIME_MODELS)
        state["memory_steward"] = {
            "model": DEEPSEEK_RUNTIME_MODELS["balanced"],
            "thinking": False,
            "execution": "background",
            "max_jobs_per_turn": 4,
        }
    if provider == "voice":
        state.update(
            {
                "asr_model": stored.get("asr_model") or DEFAULTS[provider]["asr_model"],
                "tts_model": stored.get("tts_model") or DEFAULTS[provider]["tts_model"],
                "tts_voice": stored.get("tts_voice") or DEFAULTS[provider]["tts_voice"],
                "vendor": _voice_vendor(base_url),
            }
        )
    return state


def _safe_generic_base_url(value: object) -> str:
    base_url = str(value or "").strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Vision/voice Base URL must be a public HTTPS endpoint")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        raise ValueError("Private integration endpoints are not accepted")
    return base_url


def _voice_vendor(base_url: object) -> str:
    host = (urlparse(str(base_url or "")).hostname or "").lower()
    if host in {"api.siliconflow.cn", "api.siliconflow.com"}:
        return "siliconflow"
    return "openai_compatible"


def _provider_request(
    provider: str,
    secret: str,
    config: dict[str, object],
    *,
    timeout: float = 12.0,
) -> None:
    headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
    if provider == "deepseek":
        response = httpx.get(
            f"{DEFAULTS[provider]['base_url']}/models", headers=headers, timeout=timeout
        )
    elif provider == "tavily":
        response = httpx.post(
            f"{DEFAULTS[provider]['base_url']}/search",
            headers=headers,
            json={"query": "Warehouse OS connectivity check", "max_results": 1},
            timeout=timeout,
        )
    else:
        base_url = _safe_generic_base_url(config.get("base_url"))
        response = httpx.get(f"{base_url}/models", headers=headers, timeout=timeout)
    response.raise_for_status()


def validate_credentials(provider: str, secret: str, config: dict[str, object]) -> ValidationResult:
    started = perf_counter()
    try:
        _provider_request(provider, secret, config)
    except (httpx.HTTPError, ValueError) as exc:
        return ValidationResult(
            ok=False,
            latency_ms=round((perf_counter() - started) * 1000),
            error=str(exc)[:500],
        )
    return ValidationResult(ok=True, latency_ms=round((perf_counter() - started) * 1000))


def save_configuration(
    actor: ActorContext,
    provider: str,
    api_key: str,
    payload: dict[str, object],
    settings: Settings,
) -> tuple[dict[str, object], ValidationResult]:
    provider = normalize_provider(provider)
    secret = api_key.strip()
    if not secret:
        raise ValueError("API key is required")
    existing = _stored(actor, provider)
    config = {
        "provider": provider,
        "secret_ciphertext": _encrypt(secret, settings),
        "key_hint": f"{secret[:4]}…{secret[-4:]}" if len(secret) >= 10 else "••••",
        "model": str(
            payload.get("model")
            or existing.get("model")
            or DEFAULTS[provider]["model"]
        ),
        "base_url": str(
            payload.get("base_url")
            or existing.get("base_url")
            or DEFAULTS[provider]["base_url"]
        ),
        "updated_at": datetime.now(UTC).isoformat(),
        "connection_status": "pending_validation",
        "last_error": None,
    }
    if provider == "voice":
        config.update(
            {
                "asr_model": _voice_identifier(
                    payload.get("asr_model")
                    or existing.get("asr_model")
                    or DEFAULTS[provider]["asr_model"],
                    "ASR model",
                ),
                "tts_model": _voice_identifier(
                    payload.get("tts_model")
                    or existing.get("tts_model")
                    or DEFAULTS[provider]["tts_model"],
                    "TTS model",
                ),
                "tts_voice": _voice_identifier(
                    payload.get("tts_voice")
                    or existing.get("tts_voice")
                    or DEFAULTS[provider]["tts_voice"],
                    "TTS voice",
                ),
            }
        )
    result = validate_credentials(provider, secret, config)
    config.update(
        {
            "connection_status": "connected" if result.ok else "failed",
            "checked_at": datetime.now(UTC).isoformat(),
            "last_error": result.error,
        }
    )
    _write(actor, provider, config)
    return public_state(actor, provider), result


def validate_saved(
    actor: ActorContext, provider: str, settings: Settings
) -> tuple[dict[str, object], ValidationResult]:
    provider = normalize_provider(provider)
    stored = _stored(actor, provider)
    secret = _decrypt(stored, settings)
    if not secret:
        result = ValidationResult(False, 0, "API key is not configured")
        return public_state(actor, provider), result
    result = validate_credentials(provider, secret, stored)
    stored.pop("api_key", None)
    stored["secret_ciphertext"] = _encrypt(secret, settings)
    stored["key_hint"] = stored.get("key_hint") or (
        f"{secret[:4]}…{secret[-4:]}" if len(secret) >= 10 else "••••"
    )
    stored.update(
        {
            "connection_status": "connected" if result.ok else "failed",
            "checked_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "last_error": result.error,
        }
    )
    _write(actor, provider, stored)
    return public_state(actor, provider), result


def _voice_identifier(value: object, label: str) -> str:
    normalized = str(value or "").strip()
    if (
        not normalized
        or len(normalized) > 200
        or any(not (character.isalnum() or character in "/._:-") for character in normalized)
    ):
        raise ValueError(f"Voice {label} is invalid")
    return normalized


def _voice_runtime(actor: ActorContext, settings: Settings) -> VoiceRuntime:
    stored = _stored(actor, "voice")
    try:
        secret = _decrypt(stored, settings)
    except ValueError as exc:
        raise VoiceIntegrationError(
            "voice_credential_unreadable",
            "雲端語音憑證無法讀取，請管理員重新保存語音配置",
            503,
        ) from exc
    if not secret or str(stored.get("connection_status") or "") != "connected":
        raise VoiceIntegrationError(
            "voice_not_connected",
            "雲端語音尚未連接，請管理員在系統設置中驗證語音配置",
            503,
        )
    try:
        base_url = _safe_generic_base_url(
            stored.get("base_url") or DEFAULTS["voice"]["base_url"]
        )
        asr_model = _voice_identifier(
            stored.get("asr_model") or DEFAULTS["voice"]["asr_model"], "ASR model"
        )
        tts_model = _voice_identifier(
            stored.get("tts_model") or DEFAULTS["voice"]["tts_model"], "TTS model"
        )
        tts_voice = _voice_identifier(
            stored.get("tts_voice") or DEFAULTS["voice"]["tts_voice"], "TTS voice"
        )
    except ValueError as exc:
        raise VoiceIntegrationError(
            "voice_configuration_invalid",
            "雲端語音配置不完整，請管理員重新保存并驗證",
            503,
        ) from exc
    return VoiceRuntime(
        base_url=base_url,
        api_key=secret,
        asr_model=asr_model,
        tts_model=tts_model,
        tts_voice=tts_voice,
        vendor=_voice_vendor(base_url),
    )


def _voice_model_catalog(runtime: VoiceRuntime) -> tuple[frozenset[str] | None, str]:
    """Observe SiliconFlow's account-scoped model catalog without exposing its key."""
    cache_key = hashlib.sha256(
        f"{runtime.base_url}\0{runtime.api_key}".encode()
    ).hexdigest()
    now = perf_counter()
    cached = _VOICE_CATALOG_CACHE.get(cache_key)
    if cached and cached[0] > now:
        return cached[1], cached[2]
    try:
        response = httpx.get(
            f"{runtime.base_url}/models",
            headers={"Authorization": f"Bearer {runtime.api_key}"},
            timeout=httpx.Timeout(8.0, connect=5.0),
        )
    except httpx.RequestError:
        result: tuple[frozenset[str] | None, str] = (None, "catalog_unreachable")
    else:
        if response.status_code in {401, 403}:
            result = (frozenset(), "credential_rejected")
        elif not response.is_success:
            result = (None, "catalog_unavailable")
        else:
            try:
                body = response.json()
            except ValueError:
                result = (None, "catalog_response_invalid")
            else:
                rows = body.get("data") if isinstance(body, dict) else None
                if not isinstance(rows, list):
                    result = (None, "catalog_response_invalid")
                else:
                    result = (
                        frozenset(
                            str(item["id"])
                            for item in rows
                            if isinstance(item, dict)
                            and isinstance(item.get("id"), str)
                            and item["id"].strip()
                        ),
                        "ok",
                    )
    ttl = (
        VOICE_CATALOG_CACHE_SECONDS
        if result[1] == "ok"
        else VOICE_CATALOG_FAILURE_CACHE_SECONDS
    )
    _VOICE_CATALOG_CACHE[cache_key] = (now + ttl, result[0], result[1])
    if len(_VOICE_CATALOG_CACHE) > 256:
        for key, value in list(_VOICE_CATALOG_CACHE.items()):
            if value[0] <= now:
                _VOICE_CATALOG_CACHE.pop(key, None)
    return result


def voice_capability_state(
    actor: ActorContext, settings: Settings
) -> dict[str, object]:
    state = public_state(actor, "voice")
    stored = _stored(actor, "voice")
    credential_ready = False
    try:
        credential_ready = bool(_decrypt(stored, settings))
    except ValueError:
        credential_ready = False
    adapter_ready = False
    try:
        _safe_generic_base_url(state.get("base_url"))
        _voice_identifier(state.get("asr_model"), "ASR model")
        _voice_identifier(state.get("tts_model"), "TTS model")
        _voice_identifier(state.get("tts_voice"), "TTS voice")
        adapter_ready = True
    except ValueError:
        adapter_ready = False
    connected = bool(state.get("connected") and credential_ready)
    asr_ready = bool(connected and adapter_ready and state.get("asr_model"))
    tts_ready = bool(connected and adapter_ready and state.get("tts_model"))
    catalog_status = "not_required"
    asr_reason: str | None = None
    tts_reason: str | None = None
    if connected and adapter_ready and state.get("vendor") == "siliconflow":
        try:
            runtime = _voice_runtime(actor, settings)
            catalog, catalog_status = _voice_model_catalog(runtime)
        except VoiceIntegrationError:
            catalog, catalog_status = None, "configuration_unavailable"
        if catalog is None:
            asr_ready = False
            tts_ready = False
            asr_reason = catalog_status
            tts_reason = catalog_status
        else:
            asr_ready = runtime.asr_model in catalog
            tts_ready = runtime.tts_model in catalog
            if not asr_ready:
                asr_reason = "model_unavailable"
            if not tts_ready:
                tts_reason = "model_unavailable"
    connection_status = str(state.get("connection_status") or "not_configured")
    if state.get("configured") and not credential_ready:
        connection_status = "credential_unreadable"
    if asr_ready and tts_ready:
        capability_status = "ready"
    elif asr_ready or tts_ready:
        capability_status = "partial"
    elif connected:
        capability_status = "unavailable"
    else:
        capability_status = connection_status
    return {
        **state,
        "status": capability_status,
        "available": asr_ready or tts_ready,
        "connected": connected,
        "connection_status": connection_status,
        "asr": asr_ready,
        "tts": tts_ready,
        "asr_ready": asr_ready,
        "tts_ready": tts_ready,
        "adapter_ready": adapter_ready,
        "adapter_version": "warehouse.voice.v1",
        "catalog_status": catalog_status,
        "asr_reason": asr_reason,
        "tts_reason": tts_reason,
    }


def _voice_audio_signature_valid(payload: bytes, extension: str) -> bool:
    prefix = payload[:64]
    if extension == "webm":
        return prefix.startswith(b"\x1aE\xdf\xa3")
    if extension in {"mp4", "m4a"}:
        return b"ftyp" in prefix[:32]
    if extension == "wav":
        return prefix.startswith(b"RIFF") and prefix[8:12] == b"WAVE"
    if extension in {"ogg", "opus"}:
        return prefix.startswith(b"OggS")
    if extension == "mp3":
        return prefix.startswith(b"ID3") or any(
            prefix[index] == 0xFF and prefix[index + 1] & 0xE0 == 0xE0
            for index in range(max(0, len(prefix) - 1))
        )
    return False


def _voice_provider_error(response: httpx.Response, operation: str) -> VoiceIntegrationError:
    provider_status = response.status_code
    provider_code = ""
    provider_message = ""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            provider_code = str(error.get("code") or body.get("code") or "")
            provider_message = str(error.get("message") or body.get("message") or "")
        else:
            provider_code = str(body.get("code") or "")
            provider_message = str(body.get("message") or error or "")
    unavailable_model = provider_code in {"20012", "30003"} or any(
        marker in provider_message.lower()
        for marker in ("model disabled", "model does not exist")
    )
    if operation == "transcription" and unavailable_model:
        return VoiceIntegrationError(
            "voice_asr_model_unavailable",
            "目前的雲端語音帳號未開通識別模型，已改用瀏覽器語音識別",
            503,
        )
    if provider_status == 429:
        return VoiceIntegrationError(
            "voice_rate_limited", "雲端語音服務繁忙，請稍後重試", 429
        )
    if provider_status in {401, 403}:
        return VoiceIntegrationError(
            "voice_credential_rejected",
            "雲端語音憑證已被供應商拒絕，請管理員重新驗證",
            502,
        )
    if provider_status >= 500:
        return VoiceIntegrationError(
            "voice_provider_unavailable", "雲端語音服務暫時不可用，請稍後重試", 503
        )
    return VoiceIntegrationError(
        f"voice_{operation}_rejected", "雲端語音無法處理本次請求", 502
    )


def transcribe_voice_audio(
    actor: ActorContext,
    settings: Settings,
    audio: bytes,
    content_type: str,
    language: str = "zh",
) -> VoiceTranscription:
    payload = bytes(audio or b"")
    if len(payload) < 200:
        raise VoiceIntegrationError("voice_audio_too_short", "錄音為空或太短", 422)
    if len(payload) > VOICE_MAX_AUDIO_BYTES:
        raise VoiceIntegrationError("voice_audio_too_large", "錄音超過 8 MiB 上限", 413)
    media_type = str(content_type or "").split(";", 1)[0].strip().lower()
    extension = VOICE_AUDIO_TYPES.get(media_type)
    if not extension:
        raise VoiceIntegrationError(
            "voice_audio_type_unsupported", "不支援此錄音格式", 415
        )
    if not _voice_audio_signature_valid(payload, extension):
        raise VoiceIntegrationError(
            "voice_audio_signature_invalid", "錄音內容与声明的格式不匹配", 415
        )
    runtime = _voice_runtime(actor, settings)
    data = {"model": runtime.asr_model}
    normalized_language = str(language or "").strip().lower()
    if runtime.vendor != "siliconflow" and 1 <= len(normalized_language) <= 16:
        data["language"] = normalized_language
    try:
        response = httpx.post(
            f"{runtime.base_url}/audio/transcriptions",
            headers={"Authorization": f"Bearer {runtime.api_key}"},
            data=data,
            files={"file": (f"recording.{extension}", payload, media_type)},
            timeout=httpx.Timeout(45.0, connect=10.0),
        )
    except httpx.TimeoutException as exc:
        raise VoiceIntegrationError(
            "voice_transcription_timeout", "雲端語音識別逾時，請重試", 504
        ) from exc
    except httpx.RequestError as exc:
        raise VoiceIntegrationError(
            "voice_transcription_connection_failed", "無法連接雲端語音服務", 503
        ) from exc
    if not response.is_success:
        raise _voice_provider_error(response, "transcription")
    try:
        body = response.json()
    except ValueError as exc:
        raise VoiceIntegrationError(
            "voice_transcription_response_invalid", "雲端語音服務返回了無效結果", 502
        ) from exc
    text_value = str(body.get("text") or "").strip() if isinstance(body, dict) else ""
    if not text_value:
        raise VoiceIntegrationError(
            "voice_transcription_empty", "未識別到清晰的語音內容", 422
        )
    return VoiceTranscription(
        text=text_value,
        model=runtime.asr_model,
        trace_id=response.headers.get("x-siliconcloud-trace-id"),
    )


def correct_voice_transcript(
    actor: ActorContext, settings: Settings, transcript: str
) -> tuple[str, bool]:
    raw = str(transcript or "").strip()
    if len(raw) < 2:
        return raw, False
    try:
        connection = connected_deepseek(actor, settings)
        corrected = chat_completion(
            connection,
            system_prompt=(
                "你是中文語音識別文本糾錯器。只修正明顯同音錯字并補必要標點；"
                "不得改寫原意、回答問題或添加內容。只輸出修正後純文本。"
            ),
            user_prompt=raw,
            timeout=12.0,
            thinking=False,
            max_tokens=300,
        ).strip().strip("\"'“”‘’")
    except (ValueError, httpx.HTTPError):
        return raw, False
    if not corrected or len(corrected) > len(raw) * 2 + 20:
        return raw, False
    return corrected, corrected != raw


def _voice_mp3_valid(payload: bytes) -> bool:
    prefix = payload[:64]
    return prefix.startswith(b"ID3") or any(
        prefix[index] == 0xFF and prefix[index + 1] & 0xE0 == 0xE0
        for index in range(max(0, len(prefix) - 1))
    )


def synthesize_voice_speech(
    actor: ActorContext, settings: Settings, text_value: str
) -> VoiceSpeech:
    clean = " ".join(str(text_value or "").split()).strip()
    if not clean:
        raise VoiceIntegrationError("voice_speech_empty", "沒有可朗讀的文字", 422)
    if len(clean) > VOICE_MAX_SPEECH_CHARS:
        clean = clean[:VOICE_MAX_SPEECH_CHARS]
    runtime = _voice_runtime(actor, settings)
    try:
        response = httpx.post(
            f"{runtime.base_url}/audio/speech",
            headers={
                "Authorization": f"Bearer {runtime.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": runtime.tts_model,
                "input": clean,
                "voice": runtime.tts_voice,
                "response_format": "mp3",
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
    except httpx.TimeoutException as exc:
        raise VoiceIntegrationError(
            "voice_speech_timeout", "雲端語音合成逾時，已改用瀏覽器朗讀", 504
        ) from exc
    except httpx.RequestError as exc:
        raise VoiceIntegrationError(
            "voice_speech_connection_failed", "無法連接雲端語音服務", 503
        ) from exc
    if not response.is_success:
        raise _voice_provider_error(response, "speech")
    audio = bytes(response.content)
    if len(audio) < 200 or len(audio) > VOICE_MAX_SPEECH_BYTES or not _voice_mp3_valid(audio):
        raise VoiceIntegrationError(
            "voice_speech_response_invalid", "雲端語音服務返回了無效音頻", 502
        )
    return VoiceSpeech(
        audio=audio,
        content_type="audio/mpeg",
        model=runtime.tts_model,
        trace_id=response.headers.get("x-siliconcloud-trace-id"),
    )


def tavily_search(
    actor: ActorContext,
    settings: Settings,
    payload: dict[str, object],
) -> dict[str, object]:
    """Search through the tenant-owned Tavily connection.

    Credential lookup remains tenant/RLS scoped and the secret is never placed
    in the response or audit payload.
    """

    query = str(payload.get("query") or "").strip()
    if not query:
        raise ValueError("Search query is required")
    try:
        max_results = max(1, min(int(payload.get("max_results") or 5), 20))
    except (TypeError, ValueError) as exc:
        raise ValueError("max_results must be an integer") from exc
    stored = _stored(actor, "tavily")
    secret = _decrypt(stored, settings)
    if not secret or str(stored.get("connection_status") or "") != "connected":
        raise ValueError("Tavily integration is not connected for this tenant")
    response = httpx.post(
        f"{DEFAULTS['tavily']['base_url']}/search",
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
        },
        json={
            "query": query,
            "max_results": max_results,
            "topic": str(payload.get("topic") or "general"),
            "include_answer": True,
        },
        timeout=20.0,
    )
    response.raise_for_status()
    body = response.json()
    results = body.get("results") if isinstance(body, dict) else None
    return {
        "ok": True,
        "provider": "tavily",
        "query": query,
        "answer": body.get("answer") if isinstance(body, dict) else None,
        "results": results if isinstance(results, list) else [],
        "effect_verified": True,
    }


def connected_deepseek(actor: ActorContext, settings: Settings) -> ModelConnection:
    """Return the validated model connection without exposing it to a surface.

    AI secretary, Super Terminal, embedded assistants, and mobile clients all
    enter Auto Runtime.  They must not receive a provider credential, command
    catalogue, or tool dispatcher of their own.
    """
    stored = _stored(actor, "deepseek")
    secret = _decrypt(stored, settings)
    if not secret:
        raise ValueError("AI engine is not configured for this company")
    if str(stored.get("connection_status")) != "connected":
        raise ValueError("AI engine key has not passed validation")
    return ModelConnection(
        # DeepSeek's connection check intentionally uses the canonical public
        # endpoint; surfaces must not turn a tenant configuration document into
        # an arbitrary outbound Runtime destination.
        base_url=str(DEFAULTS["deepseek"]["base_url"]).rstrip("/"),
        model=str(stored.get("model") or DEFAULTS["deepseek"]["model"]),
        api_key=secret,
    )
