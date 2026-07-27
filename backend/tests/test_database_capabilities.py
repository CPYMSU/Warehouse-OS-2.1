from app.db import session


def test_database_is_available_requires_postgresql_18_and_pgvector(monkeypatch) -> None:
    monkeypatch.setattr(
        session,
        "database_capabilities",
        lambda: {"server_version_num": 180004, "pgvector_enabled": True},
    )

    assert session.database_is_available() is True


def test_database_is_available_rejects_missing_required_capabilities(monkeypatch) -> None:
    monkeypatch.setattr(
        session,
        "database_capabilities",
        lambda: {"server_version_num": 180004, "pgvector_enabled": False},
    )
    assert session.database_is_available() is False

    monkeypatch.setattr(
        session,
        "database_capabilities",
        lambda: {"server_version_num": 170010, "pgvector_enabled": True},
    )
    assert session.database_is_available() is False
