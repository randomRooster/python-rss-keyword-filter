"""Command-line interface for rss filtering."""
import argparse
from . import feed


def _split_csv(s: str):
    return [p.strip() for p in s.split(",") if p.strip()]


def main(argv=None):
    parser = argparse.ArgumentParser(prog="rss-filter", description="Filter RSS items by <itunes:keywords>.")
    parser.add_argument("source", help="URL or local file path to RSS feed")
    parser.add_argument("--include", help="Comma-separated keywords to include", type=_split_csv)
    parser.add_argument("--exclude", help="Comma-separated keywords to exclude", type=_split_csv)
    parser.add_argument("--regex", help="Regex to match the keywords text")
    parser.add_argument("--output", help="Write filtered feed to this file (otherwise prints to stdout)")

    args = parser.parse_args(argv)

    out = feed.process(args.source, include=args.include, exclude=args.exclude, regex=args.regex, output=args.output)

    if not args.output:
        import sys
        sys.stdout.buffer.write(out)


if __name__ == "__main__":
    main()
