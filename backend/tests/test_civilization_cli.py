from app.civilization_cli import CLI_COMMANDS, KEY_ENV, build_parser


def test_civilization_cli_is_content_first_and_never_accepts_a_key_argument() -> None:
    parser = build_parser()
    help_text = parser.format_help()

    assert KEY_ENV == "WAREHOUSE_CIVILIZATION_KEY"
    assert "post list|show|create|delete" in CLI_COMMANDS
    assert "draft save" in CLI_COMMANDS
    assert "publish" in CLI_COMMANDS
    assert "share enable|disable" in CLI_COMMANDS
    assert "restore" in CLI_COMMANDS
    assert "--key-file" in help_text
    assert "--key " not in help_text


def test_civilization_cli_draft_contract_carries_revision_and_content() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "draft",
            "save",
            "--post",
            "00000000-0000-0000-0000-000000000001",
            "--revision",
            "4",
            "--content",
            "@content.json",
        ]
    )

    assert args.group == "draft"
    assert args.action == "save"
    assert args.revision == 4
    assert args.content == "@content.json"


def test_civilization_cli_share_contract_requires_post_and_revision() -> None:
    args = build_parser().parse_args(
        [
            "share",
            "enable",
            "--post",
            "00000000-0000-0000-0000-000000000001",
            "--revision",
            "7",
        ]
    )

    assert args.group == "share"
    assert args.action == "enable"
    assert args.revision == 7
