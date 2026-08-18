# GitHub REST API Reference

## Base URL
`https://api.github.com`

## Authentication
```
Authorization: Bearer <PAT>
X-GitHub-Api-Version: 2022-11-28
```

## Rate Limits

| Type | Limit | Notes |
|------|-------|-------|
| Unauthenticated | 60 req/hour | IP-based |
| Authenticated (PAT) | 5,000 req/hour | Per user |
| Secondary rate limit | 900 points/min | GET=1pt, POST=5pt |
| Max concurrent | 100 requests | |

## Key Endpoints Used

### User Profile
```
GET /users/{username}
```
- Returns: login, name, bio, blog, twitter_username, company, location, email, public_repos, followers, following, created_at
- Cache TTL: 900s (15 min)

### User Following
```
GET /users/{username}/following?per_page=30&page=1
```
- Returns: list of user objects the user follows
- Pagination: Link header
- Cache TTL: 3600s (1 hour)

### User Starred Repos
```
GET /users/{username}/starred?per_page=30&page=1
```
- Returns: list of repo objects with starred_at timestamp
- Pagination: Link header
- Cache TTL: 3600s (1 hour)

### User Public Events
```
GET /users/{username}/events/public?per_page=30&page=1
```
- Returns: PushEvent, ForkEvent, IssuesEvent, PullRequestEvent, CreateEvent, WatchEvent, ReleaseEvent
- Pagination: Link header
- Cache TTL: 300s (5 min) — events change frequently

### User Repos
```
GET /users/{username}/repos?per_page=30&page=1
```
- Returns: repo objects with metadata
- Pagination: Link header
- Cache TTL: 3600s (1 hour)

## Response Headers to Monitor
- `x-ratelimit-remaining` — remaining requests
- `x-ratelimit-reset` — Unix timestamp when limit resets
- `retry-after` — seconds to wait (on 429)

## Best Practices
1. Always authenticate for higher limits
2. Respect Retry-After headers
3. Use conditional requests (If-None-Match/ETags) for cache validation
4. Avoid concurrent bursts — serialize requests
5. Search API has stricter limits (30 req/min authenticated)
