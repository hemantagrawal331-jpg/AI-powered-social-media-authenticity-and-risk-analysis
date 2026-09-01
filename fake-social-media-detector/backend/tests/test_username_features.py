from app.intelligence.username_features import username_structure


def test_numeric_padding_changes_structure():
    short = username_structure("john_smith", "John Smith")
    long = username_structure("john_smith_84738291", "John Smith")
    assert float(long["numeric_suffix_length"]) > float(short["numeric_suffix_length"])
    assert float(long["digit_ratio"]) > float(short["digit_ratio"])


def test_template_user_digits():
    result = username_structure("user83929183")
    assert result["looks_templated"] is True


def test_ordinary_handle_is_not_templated():
    result = username_structure("priya.sharma.22", "Priya Sharma")
    assert result["looks_templated"] is False
    assert float(result["display_name_similarity"]) > 0.4
