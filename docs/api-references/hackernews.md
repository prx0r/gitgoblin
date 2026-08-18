# HackerNews API Reference

## Base URL
`https://hacker-news.firebaseio.com/v0`

## Authentication
None required.

## Rate Limits
- **No documented rate limit**
- Be reasonable — add 1-2s delays between batch requests

## Key Endpoints Used

### Top Stories
```
GET /v0/topstories.json
```
- Returns: array of up to 500 story IDs

### New Stories
```
GET /v0/newstories.json
```
- Returns: array of newest story IDs
- Cache TTL: 120s (2 min)

### Item Details
```
GET /v0/item/{id}.json
```
- Returns: story/comment/job/poll object with title, url, score, by, time, descendants, kids
- Cache TTL: 1800s (30 min)

### User Profile
```
GET /v0/user/{id}.json
```
- Returns: user with karma, created, about, submitted

## Response Structure
Story:
```json
{
  "id": 12345,
  "title": "...",
  "url": "https://...",
  "score": 150,
  "by": "username",
  "time": 1692000000,
  "descendants": 42,
  "kids": [12346, 12347, ...],
  "type": "story"
}
```

## Best Practices
1. Fetch story IDs first, then batch-fetch item details
2. Add 1-2s delays between batch requests
3. Cache items — they rarely change after a few hours
4. `kids` array only gives IDs; traverse tree client-side
