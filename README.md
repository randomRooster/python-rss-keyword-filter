# python-rss-filter

A small Python tool to fetch an RSS feed (or read a local copy), filter items based on the `<itunes:keywords>` node, and write the filtered feed back out.

## Features
- Reads RSS XML feeds from URL or local file
- Filter by include/exclude keyword lists, or regex, against the `itunes:keywords` text
- CLI interface for one-time/offline use
- Web server with conditional requests and caching
- Logging and metrics available for the webserver

## Quick start

1. Install dependencies:

   `python -m pip install -e .[test]`

2. Start the web server:

   `python -m rss_filter.server:run_server`

   Then visit `http://127.0.0.1:8000/docs

3. Or use the cli

   `python -m rss_filter.cli --help`

## Responsible Use Guidelines

This tool is intended for personal use on a local network, not for hosting online. If you don't know what a reverse proxy is, you shouldn't host the webserver where it's accessible to the public internet, even for personal use. Use it with the CLI instead.  
That said, the tool has been written with caching, rate-limitting, and logging to avoid propagating load from misbehaving clients upstream.

This is where the responsibility of the code ends; yours begins with how you use it. Most of these concern the use of the tool as a webserver, but common sense applies here. 

### When using the tool, keep the following in mind
 - A custom user agent for the script is configured so the hosts of the feed know who to contact if the tool is misbehaving. The default is "an-impolite-user@example.invalid". My guess is that you are not an impolite person, so change it to your email address, or an address that forwards to a mailbox you can monitor.  
 - When running as a webserver, this tool intentionally redistributes an already published feed. Check that the feed you want to redistribute permits it.  
 - This tool modifies an already published feed. If you share a link to someone else, make sure they know it's not the original, and where to find the original. The tool marks the title and description to help with this, but this may be against some feed's redistribution agreements. Make sure you check that modifiying these fields is allowed.  
 - Logs of each request are kept by default. If other people use your instance, you will be able to see when and how. Respect their privacy and make sure they know what you can see.

This all may seem overly dramatic, or a lot of effort for a simple tool, but a misbehaving robot is indistinguishable from from a DoS attack. The least you can do for a webmaster (who may also be the producer and host of the podcast you are listening to and far too busy to deal with misbehaving robots) is give them a way to let you know something is going wrong.  
And also, IP law is scary. If a feed says "Don't modify or redistribute this feed", and you do both, and then you get in trouble, don't say you weren't warned.

## LLM use (and code quality) disclosure
This code was written with help from a large language model. The output was thoroughly reviewed by me, but I am pretty bad at coding (especially with parsing regex and XML) so take that for what you will.  
Also, while the code in each of the methods is pretty fine (excluding commented out parts and TODOs sprinkled everywhere), the overall structure of the project sucks (poor seperation of logic, mostly). I'll refactor it one day, but for my uses it's certified Good Enough.