from normcore import normative


def test_normative_init_exports():
    assert "Statement" in normative.__all__
    assert "GroundSet" in normative.__all__
