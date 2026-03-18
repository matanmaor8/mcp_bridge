from codex_adapter import detect_codex_command


def test_detect_codex_command_returns_reason() -> None:
    availability = detect_codex_command("definitely_missing_codex_binary")
    assert availability.reason
