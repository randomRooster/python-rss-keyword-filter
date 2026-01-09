from rss_filter import feed


def test_include_keyword(tmp_path):
    src = "tests/fixtures/sample_feed.xml"
    out = feed.process(src, include=["python"])  # bytes
    s = out.decode()
    assert "Item Python" in s
    assert "Item Ads" not in s


def test_exclude_keyword(tmp_path):
    src = "tests/fixtures/sample_feed.xml"
    out = feed.process(src, exclude=["ads"])  # bytes
    s = out.decode()
    assert "Item Ads" not in s
    assert "Item Python" in s


def test_no_keywords_excluded_by_include():
    src = "tests/fixtures/sample_feed.xml"
    out = feed.process(src, include=["python"])  # bytes
    s = out.decode()
    assert "Item No Keywords" not in s


def test_regex_match():
    src = "tests/fixtures/sample_feed.xml"
    out = feed.process(src, regex=r"^python")  # bytes
    s = out.decode()
    assert "Item Python" in s
    assert "Item Ads" not in s
