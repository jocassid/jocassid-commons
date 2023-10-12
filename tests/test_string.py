
from jocassid_commons.string import normalize_whitespace


def test_normalize_whitespace():
    all_whitespace = "  \n\t\b\r\f"
    text_in = f"{all_whitespace}foo{all_whitespace}bar{all_whitespace}"
    assert "\b foo \b bar \b" == normalize_whitespace(text_in)
