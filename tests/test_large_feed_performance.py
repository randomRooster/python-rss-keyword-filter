import resource
import time
from lxml import etree
from rss_filter import feed


def _assert_valid_rss(output_bytes: bytes) -> None:
    root = etree.fromstring(output_bytes)
    assert etree.QName(root).localname.lower() == "rss"
    channel = root.find(".//channel")
    assert channel is not None


def test_large_feed_filter_and_resource_usage():
    source = "tests/fixtures/39c3_point_in_time_feed.xml"

    # Measure resource usage before
    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    cpu_start = usage_before.ru_utime + usage_before.ru_stime
    time_start = time.perf_counter()

    out_bytes = feed.process(source, include=["39c3-eng"])  # filter for substring token

    # Measure after
    usage_after = resource.getrusage(resource.RUSAGE_SELF)
    cpu_end = usage_after.ru_utime + usage_after.ru_stime
    time_end = time.perf_counter()

    cpu_seconds = cpu_end - cpu_start
    wall_seconds = time_end - time_start

    # ru_maxrss is platform-dependent (kilobytes on Linux); report delta
    maxrss_delta_kb = usage_after.ru_maxrss - usage_before.ru_maxrss

    # Basic validation of output structure
    _assert_valid_rss(out_bytes)

    # Ensure every remaining item contains '39c3-eng' in its keywords text
    root = etree.fromstring(out_bytes)
    items = root.findall('.//item')
    assert len(items) > 0, "Filtered feed should contain at least one item"

    for item in items:
        kws_nodes = item.xpath('./*[local-name()="keywords"]')
        kws_text = (kws_nodes[0].text or "") if kws_nodes else ""
        assert "39c3-eng" in kws_text, "All remaining items must include '39c3-eng' in itunes:keywords"

    # Report resource usage (pytest captures print output)
    print(f"CPU time used (seconds): {cpu_seconds:.6f}")
    print(f"Wall time elapsed (seconds): {wall_seconds:.6f}")
    print(f"Delta max RSS (KB): {maxrss_delta_kb}")
