# RSS/Atom Feed Reference

## Overview
Generic RSS/Atom feed parsing for technical blogs and industry-specific feeds.

## Authentication
None required (public feeds).

## Rate Limits
- No standardized limit
- Respect publisher's `robots.txt` and `Crawl-Delay`
- Check `<ttl>` element in feed (minutes between fetches)
- Add 2-5 second delay between feed fetches

## Feed Format Support
- RSS 2.0 (`<item>`)
- Atom (`<entry>`)

## Key Elements Parsed

### RSS 2.0
```xml
<item>
  <title>Article Title</title>
  <link>https://example.com/article</link>
  <pubDate>Mon, 18 Aug 2026 12:00:00 +0000</pubDate>
  <description>Article summary...</description>
</item>
```

### Atom
```xml
<entry>
  <title>Article Title</title>
  <link href="https://example.com/article"/>
  <published>2026-08-18T12:00:00Z</published>
  <summary>Article summary...</summary>
</entry>
```

## Keyword Filtering
- All fields concatenated: `f"{title} {summary}".lower()`
- Match against configured keywords
- Skip entries with no keyword matches

## Best Practices
1. Use conditional GET (If-Modified-Since) when possible
2. Cache feed content locally
3. Respect publisher's rate limits
4. Add 2-5 second delay between feeds
5. Use descriptive User-Agent with contact info
