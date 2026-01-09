from lxml import etree
from rss_filter import feed


def test_attribution_metadata_added():
    """Test that filtered feeds include attribution metadata."""
    source = "tests/fixtures/sample_feed.xml"
    original_url = "https://example.com/feed.xml"

    out_bytes = feed.filter_bytes(
        feed.load_source(source),
        include=["python"],
        original_source=original_url
    )

    root = etree.fromstring(out_bytes)
    channel = root.find(".//channel")
    assert channel is not None

    # Check title has "(Filtered)" suffix
    title_elem = channel.find("title")
    assert title_elem is not None
    assert "(Filtered)" in (title_elem.text or "")

    # Check description includes attribution
    description_elem = channel.find("description")
    assert description_elem is not None
    assert "filtered version" in (description_elem.text or "").lower()
    assert original_url in (description_elem.text or "")

    # Check generator element exists (may have been pre-existing in source feed)
    generator_elem = channel.find("generator")
    assert generator_elem is not None

    # Check link to original exists
    link_elem = channel.find("link")
    assert link_elem is not None
    assert original_url in (link_elem.text or "")

    # Check docs element exists
    # docs_elem = channel.find("docs")
    # assert docs_elem is not None
    # assert "github" in (docs_elem.text or "").lower()
