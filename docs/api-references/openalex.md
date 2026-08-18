# OpenAlex API Reference

## Base URL
`https://api.openalex.org`

## Authentication
Optional — improves rate limits:
```
?api_key=YOUR_KEY
mailto=your@email.com  # polite pool
```

## Rate Limits
- Free tier: ~$1/day usage (~10K+ requests)
- No hard req/min cap — metered by cost
- 402 status on overage

## Key Endpoints Used

### Search Works (Papers)
```
GET /works?search={query}&filter=from_publication_date:{date}&per_page=50&sort=from_publication_date:desc
```
- Returns: works with title, doi, publication_date, authorships, topics, cited_by_count
- Cursor pagination: `cursor={cursor}` for deep pages
- Cache TTL: 1800s (30 min)

### Select Fields (Reduce Cost)
```
GET /works?search={query}&select=id,doi,title,publication_date,authorships,topics,cited_by_count
```

### Filter by Date
```
GET /works?filter=from_publication_date:2026-07-01,to_publication_date:2026-08-18
```

## Response Structure
```json
{
  "results": [...],
  "meta": {
    "count": 12345,
    "cursor": "eyJw...",
    "next_cursor": "eyJw..."
  }
}
```

## Best Practices
1. Use `select=` to return only needed fields
2. Use cursor pagination (not offset) for deep pages
3. Cache aggressively — data updates daily
4. Include `mailto=` for polite pool
5. For bulk data, use Snapshot instead of API
