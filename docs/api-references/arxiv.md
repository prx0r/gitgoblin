# arXiv API Reference

## Base URL
`http://export.arxiv.org/api/query`

## Authentication
None required.

## Rate Limits
- **No hard limit published**
- **3-second delay between requests strongly encouraged**
- Max 30,000 results per query
- `max_results` capped at 2,000 per request

## Key Endpoints Used

### Search Papers
```
GET /api/query?search_query=all:{term}+AND+cat:cs.*&sortBy=submittedDate&sortOrder=descending&start=0&max_results=50
```

### Search Parameters
- `search_query`: query string
  - `all:{term}` — search all fields
  - `ti:{term}` — title only
  - `au:{term}` — author only
  - `abs:{term}` — abstract only
  - `cat:{category}` — category (cs.AI, cs.SE, etc.)
  - Boolean: `AND`, `OR`, `ANDNOT`
- `sortBy`: relevance, lastUpdatedDate, submittedDate
- `sortOrder`: ascending, descending
- `start`: offset (0-based)
- `max_results`: results per page (max 2000)

## Response Format
Atom XML:
```xml
<feed>
  <entry>
    <id>http://arxiv.org/abs/2602.00592v2</id>
    <title>...</title>
    <summary>...</summary>
    <author><name>...</name></author>
    <category term="cs.SE" label="Software Engineering"/>
    <published>2026-02-01T00:00:00Z</published>
    <link href="http://arxiv.org/abs/2602.00592v2" rel="alternate"/>
  </entry>
</feed>
```

## Best Practices
1. Always delay 3+ seconds between requests
2. Cache results — data updates once daily at midnight UTC
3. For bulk harvesting, use OAI-PMH or S3 bulk access
4. Refine queries to return <1,000 results
5. Use RSS feeds for category updates: `http://export.arxiv.org/rss/{category}`
