from app.services.rag.ollama import truncate_text


def test_truncate_text():
    assert truncate_text("abc", 10) == "abc"
    assert truncate_text("1234567890", 5) == "1234…"
