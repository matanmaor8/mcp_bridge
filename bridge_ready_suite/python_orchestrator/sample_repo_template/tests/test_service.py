from app.service import process_name


def test_process_name_returns_expected_value() -> None:
    assert process_name("Matan") == "processing Matan"

def test_process_name_returns_expected_prefix() -> None:
    assert process_name("Matan") == "processing Matan"

