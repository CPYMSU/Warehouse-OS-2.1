from __future__ import annotations

import base64
import hashlib

import pytest

from app.core.security import needs_password_rehash, verify_password
from app.import_legacy_bonfire import parse_payload


def _legacy_hash(password: str) -> str:
    rounds = 260_000
    salt = b"legacy-test-salt"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return (
        f"pbkdf2_sha256${rounds}${base64.b64encode(salt).decode()}$"
        f"{base64.b64encode(digest).decode()}"
    )


def test_legacy_pbkdf2_password_is_accepted_for_one_time_rehash() -> None:
    password_hash = _legacy_hash("correct horse battery staple")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("incorrect", password_hash)
    assert needs_password_rehash(password_hash)


def test_bonfire_payload_accepts_only_the_approved_three_identities() -> None:
    payload = {
        "tenant": {"slug": "bonfire", "name": "Bonfire", "industry_template": "research_lab"},
        "users": [
            {
                "username": "c_peiyuan@icloud.com",
                "display_name": "Cai Peiyuan",
                "password_hash": "pbkdf2_sha256$1$s$d",
                "topology_level": 8,
                "topology_title": "科研主管",
            },
            {
                "username": "alexzxczd@icloud.com",
                "display_name": "Zhao Xiaochen",
                "password_hash": "pbkdf2_sha256$1$s$d",
                "topology_level": 7,
                "topology_title": "研究主管",
            },
            {
                "username": "l_zhiheng@icloud.com",
                "display_name": "Li Zhiheng",
                "password_hash": "pbkdf2_sha256$1$s$d",
                "topology_level": 10,
                "topology_title": "總經理",
            },
        ],
    }
    parsed = parse_payload(payload)
    assert parsed.template_key == "research_lab"
    assert [user.username for user in parsed.users] == [
        "c_peiyuan@icloud.com",
        "alexzxczd@icloud.com",
        "l_zhiheng@icloud.com",
    ]

    payload["users"] = payload["users"][:2]
    with pytest.raises(ValueError, match="exactly three"):
        parse_payload(payload)
