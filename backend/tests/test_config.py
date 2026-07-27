from app.core.config import Settings


def test_settings_accepts_comma_separated_cors_origins() -> None:
    settings = Settings(
        cors_origins="http://127.0.0.1:8080, https://app.bonfirework.org",
    )

    assert settings.cors_origins == [
        "http://127.0.0.1:8080",
        "https://app.bonfirework.org",
    ]


def test_settings_keeps_a_separate_migration_database_url() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://warehouse_os:password@localhost/warehouse_os",
        migration_database_url="postgresql+psycopg://warehouse_migrator:password@localhost/warehouse_os",
    )

    assert settings.migration_database_url != settings.database_url
