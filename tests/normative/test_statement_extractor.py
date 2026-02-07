from normcore.normative.statement_extractor import StatementExtractor


def test_extract_empty_text_returns_empty():
    extractor = StatementExtractor()
    assert extractor.extract("") == []


def test_protocol_only_returns_empty():
    extractor = StatementExtractor()
    text = "Hello! How can I help you today?"
    assert extractor.extract(text) == []


def test_strips_greeting_prefix_and_keeps_normative():
    extractor = StatementExtractor()
    text = "Hello! Task A blocks Task B."
    statements = extractor.extract(text)
    assert len(statements) == 1
    assert "blocks" in statements[0].raw_text.lower()
    assert "hello" not in statements[0].raw_text.lower()


def test_strips_protocol_suffix():
    extractor = StatementExtractor()
    text = "Task A blocks Task B. I can help with more details."
    statements = extractor.extract(text)
    assert len(statements) == 1
    assert "can help" not in statements[0].raw_text.lower()


def test_personalization_is_preserved():
    extractor = StatementExtractor()
    text = "Hi! X is better for you."
    statements = extractor.extract(text)
    assert len(statements) == 1
    assert "better for you" in statements[0].raw_text.lower()
