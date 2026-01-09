from lxml import etree
from rss_filter import feed


def _assert_valid_rss(output_bytes: bytes) -> None:
    root = etree.fromstring(output_bytes)
    # Ensure root is <rss>
    assert etree.QName(root).localname.lower() == "rss"

    # Ensure there's a <channel>
    channel = root.find(".//channel")
    assert channel is not None

    # Ensure items can be found (may be zero-length after filtering, but structure must be present)
    items = channel.findall(".//item")
    assert isinstance(items, list)


def test_output_is_valid_rss():
    out = feed.process("tests/fixtures/sample_feed.xml")
    _assert_valid_rss(out)


def test_filtered_output_is_valid_rss():
    out = feed.process("tests/fixtures/sample_feed.xml", include=["python"])  # bytes
    _assert_valid_rss(out)
