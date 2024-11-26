from quantuminspire.sdk.models.cqasm_algorithm import CqasmAlgorithm


def test_get_content_type() -> None:
    p = CqasmAlgorithm(platform_name="platform", program_name="program")
    assert p.content_type.value == "quantum"


def test_get_language_name() -> None:
    p = CqasmAlgorithm(platform_name="platform", program_name="program")
    assert p.language_name == "cQASM"
