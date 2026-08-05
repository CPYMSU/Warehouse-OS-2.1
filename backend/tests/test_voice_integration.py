from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from app.api.deps import ActorContext
from app.core.config import Settings
from app.services import integrations


def _actor(*, can_use_voice: bool = True) -> ActorContext:
    return ActorContext(
        user_id=uuid4(),
        tenant_id=uuid4(),
        tenant_slug="voice-test",
        tenant_name="Voice Test",
        industry_template_key="general",
        username="voice@example.test",
        display_name="Voice Tester",
        role_level=10,
        topology_level=10,
        topology_title=None,
        permissions=frozenset({"ai.use"} if can_use_voice else set()),
    )


def _stored_voice() -> dict[str, object]:
    return {
        "api_key": "voice-test-secret-that-never-leaves-the-server",
        "base_url": "https://api.siliconflow.com/v1",
        "connection_status": "connected",
        "asr_model": "FunAudioLLM/SenseVoiceSmall",
        "tts_model": "FunAudioLLM/CosyVoice2-0.5B",
        "tts_voice": "FunAudioLLM/CosyVoice2-0.5B:anna",
    }


def _webm_audio(size: int = 512) -> bytes:
    return b"\x1aE\xdf\xa3" + b"\x00" * (size - 4)


def test_voice_capability_state_requires_a_decryptable_connected_credential(monkeypatch) -> None:
    monkeypatch.setattr(integrations, "_stored", lambda _actor, _provider: _stored_voice())
    monkeypatch.setattr(
        integrations,
        "_voice_model_catalog",
        lambda _runtime: (
            frozenset(
                {
                    "FunAudioLLM/SenseVoiceSmall",
                    "FunAudioLLM/CosyVoice2-0.5B",
                }
            ),
            "ok",
        ),
    )

    state = integrations.voice_capability_state(_actor(), Settings())

    assert state["status"] == "ready"
    assert state["asr"] is True
    assert state["tts"] is True
    assert state["adapter_ready"] is True
    assert state["adapter_version"] == "warehouse.voice.v1"
    assert "api_key" not in state


def test_voice_key_rotation_preserves_the_existing_endpoint(monkeypatch) -> None:
    existing = {
        **_stored_voice(),
        "base_url": "https://api.siliconflow.cn/v1",
    }
    written: dict[str, object] = {}
    monkeypatch.setattr(integrations, "_stored", lambda _actor, _provider: existing)
    monkeypatch.setattr(
        integrations,
        "validate_credentials",
        lambda *_args, **_kwargs: integrations.ValidationResult(True, 12),
    )
    monkeypatch.setattr(
        integrations,
        "_write",
        lambda _actor, _provider, payload: written.update(payload),
    )

    integrations.save_configuration(
        _actor(),
        "voice",
        "replacement-key-that-is-not-persisted-in-plaintext",
        {},
        Settings(),
    )

    assert integrations.DEFAULTS["voice"]["base_url"] == "https://api.siliconflow.cn/v1"
    assert written["base_url"] == "https://api.siliconflow.cn/v1"
    assert "api_key" not in written
    assert str(written["secret_ciphertext"]).startswith("fernet:v1:")


def test_voice_capability_state_reports_partial_when_account_has_tts_only(monkeypatch) -> None:
    monkeypatch.setattr(integrations, "_stored", lambda _actor, _provider: _stored_voice())
    monkeypatch.setattr(
        integrations,
        "_voice_model_catalog",
        lambda _runtime: (frozenset({"FunAudioLLM/CosyVoice2-0.5B"}), "ok"),
    )

    state = integrations.voice_capability_state(_actor(), Settings())

    assert state["status"] == "partial"
    assert state["available"] is True
    assert state["asr_ready"] is False
    assert state["asr_reason"] == "model_unavailable"
    assert state["tts_ready"] is True
    assert state["tts_reason"] is None
    assert state["catalog_status"] == "ok"


def test_voice_transcription_uses_server_credential_and_official_multipart_contract(
    monkeypatch,
) -> None:
    monkeypatch.setattr(integrations, "_stored", lambda _actor, _provider: _stored_voice())
    observed: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        observed.update(url=url, **kwargs)
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"text": "請幫我核對今天的庫存"},
            headers={"x-siliconcloud-trace-id": "voice-trace-1"},
        )

    monkeypatch.setattr(integrations.httpx, "post", fake_post)
    result = integrations.transcribe_voice_audio(
        _actor(), Settings(), _webm_audio(), "audio/webm;codecs=opus", "zh"
    )

    assert result.text == "請幫我核對今天的庫存"
    assert result.trace_id == "voice-trace-1"
    assert observed["url"] == "https://api.siliconflow.com/v1/audio/transcriptions"
    assert observed["data"] == {"model": "FunAudioLLM/SenseVoiceSmall"}
    filename, content, media_type = observed["files"]["file"]
    assert filename == "recording.webm"
    assert content == _webm_audio()
    assert media_type == "audio/webm"
    assert observed["headers"] == {
        "Authorization": "Bearer voice-test-secret-that-never-leaves-the-server"
    }


@pytest.mark.parametrize(
    ("payload", "content_type", "code", "status_code"),
    [
        (b"tiny", "audio/webm", "voice_audio_too_short", 422),
        (b"x" * 512, "text/plain", "voice_audio_type_unsupported", 415),
        (b"x" * 512, "audio/webm", "voice_audio_signature_invalid", 415),
    ],
)
def test_voice_transcription_rejects_invalid_audio_before_outbound_call(
    monkeypatch, payload: bytes, content_type: str, code: str, status_code: int
) -> None:
    monkeypatch.setattr(integrations, "_stored", lambda _actor, _provider: _stored_voice())
    monkeypatch.setattr(
        integrations.httpx,
        "post",
        lambda *_args, **_kwargs: pytest.fail("invalid audio must not reach the provider"),
    )

    with pytest.raises(integrations.VoiceIntegrationError) as raised:
        integrations.transcribe_voice_audio(
            _actor(), Settings(), payload, content_type, "zh"
        )

    assert raised.value.code == code
    assert raised.value.status_code == status_code


def test_voice_provider_errors_are_stable_and_do_not_echo_provider_body(monkeypatch) -> None:
    monkeypatch.setattr(integrations, "_stored", lambda _actor, _provider: _stored_voice())

    def fake_post(url: str, **_kwargs: object) -> httpx.Response:
        return httpx.Response(
            401,
            request=httpx.Request("POST", url),
            text="provider-secret-debug-body",
        )

    monkeypatch.setattr(integrations.httpx, "post", fake_post)
    with pytest.raises(integrations.VoiceIntegrationError) as raised:
        integrations.transcribe_voice_audio(
            _actor(), Settings(), _webm_audio(), "audio/webm", "zh"
        )

    assert raised.value.code == "voice_credential_rejected"
    assert "provider-secret-debug-body" not in raised.value.message


def test_disabled_asr_model_has_an_actionable_stable_error(monkeypatch) -> None:
    monkeypatch.setattr(integrations, "_stored", lambda _actor, _provider: _stored_voice())

    def fake_post(url: str, **_kwargs: object) -> httpx.Response:
        return httpx.Response(
            403,
            request=httpx.Request("POST", url),
            json={"code": 30003, "message": "Model disabled."},
        )

    monkeypatch.setattr(integrations.httpx, "post", fake_post)
    with pytest.raises(integrations.VoiceIntegrationError) as raised:
        integrations.transcribe_voice_audio(
            _actor(), Settings(), _webm_audio(), "audio/webm", "zh"
        )

    assert raised.value.code == "voice_asr_model_unavailable"
    assert raised.value.status_code == 503
    assert "瀏覽器語音識別" in raised.value.message


def test_voice_speech_returns_valid_mp3_and_uses_configured_voice(monkeypatch) -> None:
    monkeypatch.setattr(integrations, "_stored", lambda _actor, _provider: _stored_voice())
    observed: dict[str, object] = {}
    audio = b"ID3" + b"\x00" * 400

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        observed.update(url=url, **kwargs)
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            content=audio,
            headers={"content-type": "audio/mpeg"},
        )

    monkeypatch.setattr(integrations.httpx, "post", fake_post)
    result = integrations.synthesize_voice_speech(
        _actor(), Settings(), "  晚上好，請早些休息。  "
    )

    assert result.audio == audio
    assert result.content_type == "audio/mpeg"
    assert observed["url"] == "https://api.siliconflow.com/v1/audio/speech"
    assert observed["json"] == {
        "model": "FunAudioLLM/CosyVoice2-0.5B",
        "input": "晚上好，請早些休息。",
        "voice": "FunAudioLLM/CosyVoice2-0.5B:anna",
        "response_format": "mp3",
    }
