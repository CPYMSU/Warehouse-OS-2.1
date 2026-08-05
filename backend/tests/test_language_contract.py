from app.services.language_contract import (
    detect_locale,
    language_instruction,
    localized_empty_answer,
    message_matches_locale,
    normalize_locale,
    resolve_language_contract,
)


def test_locale_aliases_are_canonical() -> None:
    assert normalize_locale("tw") == "zh-Hant"
    assert normalize_locale("zh_CN") == "zh-Hans"
    assert normalize_locale("en-US") == "en"


def test_strong_current_turn_language_overrides_interface_in_auto_mode() -> None:
    contract = resolve_language_contract(
        "Please explain the research design and its evidence.",
        requested_locale="zh-Hant",
    )
    assert contract.locale == "en"
    assert contract.source == "current_turn"


def test_chinese_variant_detection_uses_script_evidence() -> None:
    assert detect_locale("请继续查看这个论文的数据") == "zh-Hans"
    assert detect_locale("請繼續閱覽這個論文的資料") == "zh-Hant"


def test_ambiguous_turn_falls_back_to_interface_preference() -> None:
    contract = resolve_language_contract("好", requested_locale="zh-Hans")
    assert contract.locale == "zh-Hans"
    assert contract.source == "interface_preference"


def test_explicit_turn_instruction_has_highest_auto_priority() -> None:
    contract = resolve_language_contract(
        "請用英文回答：這份論文的核心是什麼？",
        requested_locale="zh-Hant",
    )
    assert contract.locale == "en"
    assert contract.source == "explicit_turn_instruction"


def test_fixed_mode_does_not_follow_detected_turn_language() -> None:
    contract = resolve_language_contract(
        "Answer this in English.",
        requested_locale="zh-Hant",
        language_mode="fixed",
    )
    assert contract.locale == "zh-Hant"
    assert contract.source == "fixed_preference"


def test_prompt_contract_protects_non_prose_tokens() -> None:
    instruction = language_instruction("zh-Hans")
    assert "简体中文" in instruction
    assert "file paths" in instruction
    assert "identifiers" in instruction
    assert localized_empty_answer("en").startswith("I understood")


def test_output_language_validator_is_conservative_but_detects_clear_mismatch() -> None:
    assert message_matches_locale("This result preserves code/main.py.", "en")
    assert not message_matches_locale("這是一段完整的繁體中文回答。", "en")
    assert not message_matches_locale(
        "This is a complete English answer with enough prose to be unambiguous.",
        "zh-Hant",
    )
    assert message_matches_locale("已完成 code/main.py 的檢查。", "zh-Hant")
