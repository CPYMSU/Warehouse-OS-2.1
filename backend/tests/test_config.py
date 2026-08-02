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


def test_hosted_storage_roots_keep_hdd_data_and_ssd_code_separate(tmp_path) -> None:
    settings = Settings(
        asset_storage_root=tmp_path / "hdd",
        asset_code_ssd_root=tmp_path / "ssd",
        hosted_runtime_data_root=tmp_path / "hdd-runtime",
        hosted_database_root=tmp_path / "hdd-databases",
    )

    assert settings.asset_storage_root != settings.asset_code_ssd_root
    assert settings.hosted_runtime_data_root.name == "hdd-runtime"
    assert settings.hosted_database_root.name == "hdd-databases"


def test_settings_accepts_comma_separated_webauthn_origins() -> None:
    settings = Settings(
        webauthn_origins="http://localhost:8080, https://app.bonfirework.org",
    )

    assert settings.webauthn_origins == [
        "http://localhost:8080",
        "https://app.bonfirework.org",
    ]


def test_settings_accepts_comma_separated_browser_origins() -> None:
    settings = Settings(
        browser_allowed_origins="http://localhost:8080, https://bonfirework.org/",
        browser_resource_origins="https://unpkg.com/, https://fonts.gstatic.com",
    )

    assert settings.browser_allowed_origins == [
        "http://localhost:8080",
        "https://bonfirework.org",
    ]
    assert settings.browser_resource_origins == [
        "https://unpkg.com",
        "https://fonts.gstatic.com",
    ]


def test_settings_normalizes_public_origin() -> None:
    settings = Settings(public_origin="https://bonfirework.org/")

    assert settings.public_origin == "https://bonfirework.org"


def test_production_public_origin_falls_back_to_verified_webauthn_origin() -> None:
    settings = Settings(
        environment="production",
        public_origin="",
        jwt_secret="j" * 40,
        integration_secret="i" * 40,
        webauthn_rp_id="bonfirework.org",
        webauthn_origins=["https://bonfirework.org"],
    )

    assert settings.public_origin == "https://bonfirework.org"
