"""Deterministic three-language contract for UI and AI response surfaces.

Language selection is application state, not a guess delegated entirely to a
model.  The model receives the resolved contract and is responsible only for
rendering user-facing prose in that language.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SUPPORTED_LOCALES = ("zh-Hant", "zh-Hans", "en")

_LOCALE_ALIASES = {
    "tw": "zh-Hant",
    "zh-tw": "zh-Hant",
    "zh-hk": "zh-Hant",
    "zh-mo": "zh-Hant",
    "zh-hant": "zh-Hant",
    "hant": "zh-Hant",
    "traditional": "zh-Hant",
    "cn": "zh-Hans",
    "zh-cn": "zh-Hans",
    "zh-sg": "zh-Hans",
    "zh-hans": "zh-Hans",
    "hans": "zh-Hans",
    "simplified": "zh-Hans",
    "en": "en",
    "en-us": "en",
    "en-gb": "en",
    "english": "en",
}

_HANT_HINTS = set(
    "體臺灣與為這個們說話對賬執審計設置資料檔案網絡連線後臺裡邊"
    "庫存總覽權限採購報表終端簡繁學術論文標題選擇繼續閱覽託管數據"
)
_HANS_HINTS = set(
    "体台湾与为这个们说话对账执审计设置资料档案网络连线后台里边"
    "库存总览权限采购报表终端简繁学术论文标题选择继续阅览托管数据"
)

_EXPLICIT_PATTERNS = (
    (
        "zh-Hant",
        re.compile(
            r"(?:用|以|請用|请用)?\s*(?:繁體中文|繁体中文|繁體|正體中文|正體)"
            r"(?:\s*(?:回答|回覆|回复|輸出|输出))?|"
            r"(?:reply|respond|answer)\s+(?:in\s+)?traditional\s+chinese",
            re.IGNORECASE,
        ),
    ),
    (
        "zh-Hans",
        re.compile(
            r"(?:用|以|請用|请用)?\s*(?:簡體中文|简体中文|簡體|简体)"
            r"(?:\s*(?:回答|回覆|回复|輸出|输出))?|"
            r"(?:reply|respond|answer)\s+(?:in\s+)?simplified\s+chinese",
            re.IGNORECASE,
        ),
    ),
    (
        "en",
        re.compile(
            r"(?:用|以|請用|请用)\s*(?:英文|英語|英语)(?:\s*(?:回答|回覆|回复|輸出|输出))?|"
            r"(?:reply|respond|answer)\s+(?:to\s+me\s+)?(?:in\s+)?english|"
            r"\bin\s+english\b",
            re.IGNORECASE,
        ),
    ),
)


@dataclass(frozen=True)
class LanguageContract:
    locale: str
    source: str
    requested_locale: str | None
    detected_locale: str | None
    mode: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "locale": self.locale,
            "source": self.source,
            "requested_locale": self.requested_locale,
            "detected_locale": self.detected_locale,
            "mode": self.mode,
        }


def normalize_locale(value: object, *, fallback: str | None = "zh-Hant") -> str | None:
    compact = str(value or "").strip().lower().replace("_", "-")
    if compact in _LOCALE_ALIASES:
        return _LOCALE_ALIASES[compact]
    if compact.startswith("en-"):
        return "en"
    if compact.startswith("zh-hant"):
        return "zh-Hant"
    if compact.startswith("zh-hans"):
        return "zh-Hans"
    return fallback


def explicit_locale(text: object) -> str | None:
    source = str(text or "")
    for locale, pattern in _EXPLICIT_PATTERNS:
        if pattern.search(source):
            return locale
    return None


def detect_locale(text: object) -> str | None:
    """Return only a strong signal; ambiguous Chinese defers to UI state."""
    source = str(text or "")
    explicit = explicit_locale(source)
    if explicit:
        return explicit
    latin_count = len(re.findall(r"[A-Za-z]", source))
    han = re.findall(r"[\u3400-\u9fff]", source)
    han_count = len(han)
    if latin_count >= 6 and latin_count >= max(6, han_count * 2):
        return "en"
    hant_count = sum(character in _HANT_HINTS for character in han)
    hans_count = sum(character in _HANS_HINTS for character in han)
    if hant_count > hans_count and hant_count >= 1:
        return "zh-Hant"
    if hans_count > hant_count and hans_count >= 1:
        return "zh-Hans"
    return None


def resolve_language_contract(
    text: object,
    *,
    requested_locale: object = None,
    language_mode: object = "auto",
) -> LanguageContract:
    requested = normalize_locale(requested_locale, fallback=None)
    mode = "fixed" if str(language_mode or "").strip().lower() == "fixed" else "auto"
    detected = detect_locale(text)
    if mode == "fixed":
        return LanguageContract(
            locale=requested or "zh-Hant",
            source="fixed_preference" if requested else "platform_default",
            requested_locale=requested,
            detected_locale=detected,
            mode=mode,
        )
    explicit = explicit_locale(text)
    if explicit:
        selected, source = explicit, "explicit_turn_instruction"
    elif detected:
        selected, source = detected, "current_turn"
    elif requested:
        selected, source = requested, "interface_preference"
    else:
        selected, source = "zh-Hant", "platform_default"
    return LanguageContract(
        locale=selected,
        source=source,
        requested_locale=requested,
        detected_locale=detected,
        mode=mode,
    )


def language_instruction(locale: object) -> str:
    selected = normalize_locale(locale) or "zh-Hant"
    shared = (
        "Preserve command names, API fields, identifiers, code, file paths, URLs, "
        "citations, numbers and quoted source text exactly as supplied. "
        "Apply this rule to every user-visible JSON field, including message, plan "
        "steps, questions, warnings and errors."
    )
    if selected == "en":
        return "LANGUAGE CONTRACT: Write all user-facing prose in English. " + shared
    if selected == "zh-Hans":
        return (
            "LANGUAGE CONTRACT: 所有面向用户的文字必须使用简体中文（zh-Hans），"
            "不要混用繁体中文。 " + shared
        )
    return (
        "LANGUAGE CONTRACT: 所有面向使用者的文字必須使用繁體中文（zh-Hant），"
        "不要混用簡體中文。 " + shared
    )


def localized_runtime_error(locale: object, detail: object = None) -> str:
    """Return a stable public error without serialising provider exceptions.

    ``detail`` is accepted for call-site compatibility but is deliberately not
    rendered. Provider errors can contain prompts, SQL, URLs, credentials, or
    stack fragments and therefore belong only in protected server telemetry.
    """
    selected = normalize_locale(locale) or "zh-Hant"
    prefix = {
        "zh-Hant": "AI 服務暫時不可用",
        "zh-Hans": "AI 服务暂时不可用",
        "en": "The AI service is temporarily unavailable",
    }[selected]
    return f"⚠ {prefix}，本輪沒有執行任何未完成的操作。" if selected == "zh-Hant" else (
        f"⚠ {prefix}，本轮没有执行任何未完成的操作。"
        if selected == "zh-Hans"
        else f"⚠ {prefix}. No unfinished operation was executed in this turn."
    )


def localized_structure_failure(locale: object) -> str:
    selected = normalize_locale(locale) or "zh-Hant"
    return {
        "zh-Hant": (
            "我已理解您的要求，但本輪的內部協調結果格式異常，"
            "因此沒有冒險執行操作。請再試一次。"
        ),
        "zh-Hans": (
            "我已理解您的要求，但本轮的内部协调结果格式异常，"
            "因此没有冒险执行操作。请再试一次。"
        ),
        "en": (
            "I understood the request, but the internal coordination result was malformed, "
            "so no operation was executed. Please try again."
        ),
    }[selected]


def localized_empty_answer(locale: object) -> str:
    selected = normalize_locale(locale) or "zh-Hant"
    return {
        "zh-Hant": "我已理解這項要求，但本輪沒有產生可呈現的回答。",
        "zh-Hans": "我已理解这项要求，但本轮没有产生可呈现的回答。",
        "en": "I understood the request, but this turn produced no user-facing answer.",
    }[selected]


def localized_empty_plan(locale: object) -> str:
    selected = normalize_locale(locale) or "zh-Hant"
    return {
        "zh-Hant": "Runtime 已形成計畫，但沒有產生面向使用者的摘要。",
        "zh-Hans": "Runtime 已形成计划，但没有产生面向用户的摘要。",
        "en": "The Runtime formed a plan but produced no user-facing summary.",
    }[selected]


def message_matches_locale(value: object, locale: object) -> bool:
    """Conservatively reject only a clearly wrong user-facing language."""
    source = str(value or "")
    selected = normalize_locale(locale) or "zh-Hant"
    latin_count = len(re.findall(r"[A-Za-z]", source))
    han = re.findall(r"[\u3400-\u9fff]", source)
    han_count = len(han)
    if selected == "en":
        return not (han_count >= 6 and han_count > max(3, latin_count // 2))
    if latin_count >= 20 and latin_count > max(20, han_count * 3):
        return False
    hant_count = sum(character in _HANT_HINTS for character in han)
    hans_count = sum(character in _HANS_HINTS for character in han)
    if selected == "zh-Hant":
        return hans_count <= hant_count + 1
    return hant_count <= hans_count + 1
