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


def test_first_person_would_not_is_kept_for_refusal_eval():
    extractor = StatementExtractor()
    text = "I would not publish this yet because evidence is insufficient."
    statements = extractor.extract(text)
    assert len(statements) == 1
    assert "would not publish" in statements[0].raw_text.lower()


def test_protocol_sentence_detector_flags_marker_sentences():
    extractor = StatementExtractor()
    assert extractor._looks_like_protocol_sentence("Thanks for checking.")


def test_strip_protocol_prefix_keeps_text_after_first_normative_sentence():
    extractor = StatementExtractor()
    text = "Hello! Task A blocks Task B. I can help with more details."
    cleaned = extractor._strip_protocol_prefix_sentences(text)
    assert cleaned.startswith("Hello!")
    assert "I can help" in cleaned


def test_strip_protocol_prefix_drops_personalized_protocol_offer():
    extractor = StatementExtractor()
    text = "I can help for you. Task A blocks Task B."
    cleaned = extractor._strip_protocol_prefix_sentences(text)
    assert cleaned == "Task A blocks Task B."


def test_strip_greeting_rejects_question_without_normative_indicators():
    extractor = StatementExtractor()
    cleaned = extractor._strip_greeting("Can I help you?")
    assert cleaned == ""


def test_strip_greeting_question_tail_rejection_branch(monkeypatch):
    extractor = StatementExtractor()
    monkeypatch.setattr(extractor, "_strip_protocol_suffix", lambda text: text)
    monkeypatch.setattr(extractor, "_strip_protocol_prefix_sentences", lambda text: text)
    calls = 0

    def _fake_contains_normative(_text: str) -> bool:
        nonlocal calls
        calls += 1
        return calls == 1

    monkeypatch.setattr(extractor, "_contains_normative_indicators", _fake_contains_normative)
    cleaned = extractor._strip_greeting("Task A blocks Task B?")
    assert cleaned == ""
