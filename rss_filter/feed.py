"""Core feed parsing and filtering utilities."""
from typing import Optional, Sequence
import re
import requests
import logging
from lxml import etree

logger = logging.getLogger(__name__)

xml_parser_class = etree.XMLParser


def load_source(source: str) -> bytes:
    """Load feed bytes from a URL or local file path."""
    if source.startswith("http://") or source.startswith("https://"):
        r = requests.get(source)
        r.raise_for_status()
        return r.content
    with open(source, "rb") as fh:
        return fh.read()


def parse_feed(content: bytes) -> etree._Element:
    parser = xml_parser_class(remove_blank_text=True)
    return etree.fromstring(content, parser)


def _get_keywords_text(item: etree._Element) -> str:
    # Use XPath with local-name() to support itunes namespace variants
    keywords_nodes = item.xpath('./*[local-name()="keywords"]')
    if not keywords_nodes:
        return ""
    return (keywords_nodes[0].text or "").strip()


def _keywords_set(keywords_text: str) -> set:
    if not keywords_text:
        return set()
    return {keyword.strip().lower() for keyword in keywords_text.split(",") if keyword.strip()}


def item_matches(item: etree._Element, include: Optional[Sequence[str]] = None,
                 exclude: Optional[Sequence[str]] = None, regex: Optional[str] = None) -> bool:
    """Return True to keep item, False to remove it."""
    keywords_text = _get_keywords_text(item)
    keywords = _keywords_set(keywords_text)

    if include:
        include_set = {s.strip().lower() for s in include}
        if not (include_set & keywords):
            return False

    if exclude:
        exclude_set = {s.strip().lower() for s in exclude}
        if exclude_set & keywords:
            return False

    if regex:
        if not re.search(regex, keywords_text or ""):
            return False

    return True


def filter_feed(root: etree._Element, include=None, exclude=None, regex=None) -> int:
    """Remove items that do not satisfy the filters.
    Returns number of items remaining.
    Logs which items are kept/removed for audit trail.
    """
    item_elements = root.xpath('.//item')
    removed_count = 0
    for item_element in list(item_elements):
        if not item_matches(item_element, include=include, exclude=exclude, regex=regex):
            title_elem = item_element.find("title")
            title = (title_elem.text or "untitled") if title_elem is not None else "untitled"
            kws_elem = item_element.xpath('./*[local-name()="keywords"]')
            keywords = (kws_elem[0].text or "") if kws_elem else ""
            logger.debug(f"Filtering out item: title='{title}', keywords='{keywords}'")
            parent_element = item_element.getparent()
            if parent_element is not None:
                parent_element.remove(item_element)
            removed_count += 1
    remaining_count = len(root.xpath('.//item'))
    logger.info(f"Filtered feed: removed {removed_count} items, {remaining_count} remaining")
    return remaining_count


def serialize_feed(root: etree._Element) -> bytes:
    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="utf-8")


def add_attribution_metadata(root: etree._Element, original_source: Optional[str] = None) -> None:
    """Add attribution metadata to the feed's channel to identify it as filtered.

    Modifies the channel element in-place to add:
    - Title suffix "(Filtered)"
    - Attribution note in description
    - Generator element identifying the tool
    - Link to the original source
    - Docs link to the project repository
    """
    channel = root.find(".//channel")
    if channel is None:
        return

    # Modify title: append "(Filtered)"
    title_elem = channel.find("title")
    if title_elem is not None and title_elem.text:
        if not title_elem.text.endswith("(Filtered)"):
            title_elem.text = f"{title_elem.text} (Filtered)"

    # Add attribution note to description
    description_elem = channel.find("description")
    if description_elem is None:
        description_elem = etree.Element("description")
        channel.insert(0, description_elem)

    attribution_line = "[This is a filtered version of an RSS feed. Original source: " + (original_source or "unknown") + "]\n\n"
    current_text = description_elem.text or ""
    if attribution_line not in current_text:
        description_elem.text = attribution_line + current_text

    # Add generator element (identifies the tool)
    generator_elem = channel.find("generator")
    if generator_elem is None:
        generator_elem = etree.Element("generator")
        generator_elem.text = "python-rss-keyword-filter v0.1.0"
        channel.append(generator_elem)

    # Add link to original source
    if original_source:
        link_elem = channel.find("link")
        if link_elem is None:
            link_elem = etree.Element("link")
            link_elem.text = original_source
            channel.insert(1, link_elem)

    # Add docs link to the project
    # docs_elem = channel.find("docs")
    # if docs_elem is None:
    #     docs_elem = etree.Element("docs")
    #     docs_elem.text = "https://github.com/yourusername/python-rss-filter"
    #     channel.append(docs_elem)


# TODO: when I'm less sleepy go merge these two methods, and also extract the self-link to add it as attribution
def process(source: str, include=None, exclude=None, regex=None, output: Optional[str] = None) -> bytes:
    feed_content = load_source(source)
    root_element = parse_feed(feed_content)
    filter_feed(root_element, include=include, exclude=exclude, regex=regex)
    add_attribution_metadata(root_element, original_source="SOME SOURCE")
    output_bytes = serialize_feed(root_element)
    if output:
        with open(output, "wb") as fh:
            fh.write(output_bytes)
    return output_bytes


def filter_bytes(content: bytes, include=None, exclude=None, regex=None, original_source: Optional[str] = None) -> bytes:
    """Filter a feed provided as bytes and return the filtered feed as bytes.

    This is useful for services that fetch the bytes themselves (for example,
    to implement conditional requests / caching) and then apply the filtering
    without re-fetching.

    Args:
        content: The RSS feed as bytes.
        include: Optional list of keywords to include.
        exclude: Optional list of keywords to exclude.
        regex: Optional regex pattern to match keywords.
        original_source: Optional URL or source identifier of the original feed for attribution.

    Returns:
        The filtered feed as bytes, annotated with attribution metadata.
    """
    root_element = parse_feed(content)
    filter_feed(root_element, include=include, exclude=exclude, regex=regex)
    add_attribution_metadata(root_element, original_source=original_source)
    return serialize_feed(root_element)
