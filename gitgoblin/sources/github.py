from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from gitgoblin.http import ResilientHTTP
from gitgoblin.models import Entity, Observation, evidence_for_payload, utcnow
from gitgoblin.settings import AppSettings

API = "https://api.github.com"


def _dt(value: str | None, fallback: datetime | None = None) -> datetime:
    if value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return fallback or utcnow()


class GitHubCollector:
    source_name = "github"
    source_family = "code_host"

    def __init__(self, settings: AppSettings, http: ResilientHTTP | None = None) -> None:
        self.settings = settings
        self.http = http or ResilientHTTP(
            user_agent=settings.user_agent,
            timeout=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
        )
        token = settings.github_token()
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": settings.github.api_version,
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def collect(self, username: str, *, sector: str, pages: int | None = None) -> tuple[list[Entity], list[Observation]]:
        pages = pages or self.settings.github.pages_per_seed
        entities: dict[str, Entity] = {}
        observations: list[Observation] = []
        user = self.http.get_json(f"{API}/users/{username}", headers=self.headers, cache_ttl_seconds=900)
        user_id = f"github:user:{user['login'].lower()}"
        entities[user_id] = self._user_entity(user)
        observations.append(self._profile_observation(user, sector))

        if self.settings.github.include_following:
            for followed in self.http.paginate_json(
                f"{API}/users/{username}/following", headers=self.headers, pages=pages
            ):
                fid = f"github:user:{followed['login'].lower()}"
                entities.setdefault(fid, self._user_entity(followed))
                payload = {"actor": username, "followed": followed.get("login"), "snapshot": True}
                observations.append(
                    Observation(
                        source=self.source_name,
                        source_family=self.source_family,
                        entity_type="relationship",
                        entity_id=f"{user_id}->follow->{fid}",
                        actor_id=user_id,
                        action="follow",
                        target_id=fid,
                        occurred_at=utcnow(),  # GitHub exposes current relation, not historical follow time.
                        value={"snapshot": True},
                        sector=sector,
                        evidence=evidence_for_payload(payload, f"https://github.com/{username}?tab=following"),
                        quality={"temporal_precision": "snapshot_only"},
                    )
                )

        if self.settings.github.include_starred:
            star_headers = dict(self.headers)
            star_headers["Accept"] = "application/vnd.github.star+json"
            for item in self.http.paginate_json(
                f"{API}/users/{username}/starred", headers=star_headers, pages=pages
            ):
                repo = item.get("repo", item)
                if not isinstance(repo, dict) or not repo.get("full_name"):
                    continue
                rid = f"github:repo:{repo['full_name'].lower()}"
                entities[rid] = self._repo_entity(repo)
                starred_at = item.get("starred_at")
                payload = {"actor": username, "repo": repo.get("full_name"), "starred_at": starred_at}
                observations.append(
                    Observation(
                        source=self.source_name,
                        source_family=self.source_family,
                        entity_type="repository_interaction",
                        entity_id=f"{user_id}:star:{rid}:{starred_at or 'snapshot'}",
                        actor_id=user_id,
                        action="star",
                        target_id=rid,
                        occurred_at=_dt(starred_at),
                        value=self._repo_metrics(repo),
                        tags=repo.get("topics") or [],
                        sector=sector,
                        evidence=evidence_for_payload(payload, f"https://github.com/{repo['full_name']}"),
                        quality={"temporal_precision": "event" if starred_at else "snapshot"},
                    )
                )

        if self.settings.github.include_events:
            for event in self.http.paginate_json(
                f"{API}/users/{username}/events/public", headers=self.headers, pages=pages
            ):
                parsed = self._event_observation(event, sector)
                if parsed:
                    observations.append(parsed)
                    repo_name = (event.get("repo") or {}).get("name")
                    if repo_name:
                        rid = f"github:repo:{repo_name.lower()}"
                        entities.setdefault(
                            rid,
                            Entity(
                                entity_id=rid,
                                entity_type="repository",
                                name=repo_name,
                                source="github",
                                url=f"https://github.com/{repo_name}",
                                attrs={},
                            ),
                        )

        if self.settings.github.include_repositories:
            for repo in self.http.paginate_json(
                f"{API}/users/{username}/repos",
                headers=self.headers,
                params={"sort": "pushed", "direction": "desc"},
                pages=pages,
            ):
                rid = f"github:repo:{repo['full_name'].lower()}"
                entities[rid] = self._repo_entity(repo)
                observations.append(
                    Observation(
                        source=self.source_name,
                        source_family=self.source_family,
                        entity_type="repository",
                        entity_id=rid,
                        actor_id=user_id,
                        action="owns" if not repo.get("fork") else "fork_owns",
                        target_id=rid,
                        occurred_at=_dt(repo.get("created_at")),
                        value=self._repo_metrics(repo),
                        tags=repo.get("topics") or [],
                        sector=sector,
                        evidence=evidence_for_payload(repo, repo.get("html_url"), str(repo.get("id"))),
                    )
                )
        return list(entities.values()), observations

    @staticmethod
    def _user_entity(user: dict[str, Any]) -> Entity:
        login = user.get("login") or user.get("name") or "unknown"
        return Entity(
            entity_id=f"github:user:{login.lower()}",
            entity_type="developer",
            name=login,
            source="github",
            url=user.get("html_url") or f"https://github.com/{login}",
            attrs={
                "followers": user.get("followers"),
                "following": user.get("following"),
                "public_repos": user.get("public_repos"),
                "company": user.get("company"),
                "blog": user.get("blog"),
                "location": user.get("location"),
                "created_at": user.get("created_at"),
                "bio": user.get("bio"),
            },
        )

    @staticmethod
    def _repo_entity(repo: dict[str, Any]) -> Entity:
        full_name = repo["full_name"]
        license_obj = repo.get("license") or {}
        return Entity(
            entity_id=f"github:repo:{full_name.lower()}",
            entity_type="repository",
            name=full_name,
            source="github",
            url=repo.get("html_url") or f"https://github.com/{full_name}",
            attrs={
                **GitHubCollector._repo_metrics(repo),
                "description": repo.get("description"),
                "topics": repo.get("topics") or [],
                "language": repo.get("language"),
                "created_at": repo.get("created_at"),
                "pushed_at": repo.get("pushed_at"),
                "license_spdx": license_obj.get("spdx_id"),
                "fork": bool(repo.get("fork")),
                "owner": (repo.get("owner") or {}).get("login"),
            },
        )

    @staticmethod
    def _repo_metrics(repo: dict[str, Any]) -> dict[str, Any]:
        return {
            "stars": int(repo.get("stargazers_count") or 0),
            "forks": int(repo.get("forks_count") or repo.get("forks") or 0),
            "open_issues": int(repo.get("open_issues_count") or 0),
            "size_kb": int(repo.get("size") or 0),
            "created_at": repo.get("created_at"),
            "pushed_at": repo.get("pushed_at"),
            "language": repo.get("language"),
        }

    def _profile_observation(self, user: dict[str, Any], sector: str) -> Observation:
        uid = f"github:user:{user['login'].lower()}"
        return Observation(
            source=self.source_name,
            source_family=self.source_family,
            entity_type="developer",
            entity_id=uid,
            actor_id=uid,
            action="profile_snapshot",
            target_id=uid,
            occurred_at=utcnow(),
            value={
                "followers": int(user.get("followers") or 0),
                "following": int(user.get("following") or 0),
                "public_repos": int(user.get("public_repos") or 0),
                "created_at": user.get("created_at"),
                "company": user.get("company"),
            },
            sector=sector,
            evidence=evidence_for_payload(user, user.get("html_url"), str(user.get("id"))),
            quality={"temporal_precision": "snapshot"},
        )

    def _event_observation(self, event: dict[str, Any], sector: str) -> Observation | None:
        mapping = {
            "WatchEvent": "star",
            "ForkEvent": "fork",
            "IssuesEvent": "issue",
            "PullRequestEvent": "pull_request",
            "PushEvent": "push",
            "CreateEvent": "create",
            "ReleaseEvent": "release",
        }
        action = mapping.get(event.get("type"))
        if not action:
            return None
        actor = (event.get("actor") or {}).get("login")
        repo_name = (event.get("repo") or {}).get("name")
        if not actor or not repo_name:
            return None
        actor_id = f"github:user:{actor.lower()}"
        target_id = f"github:repo:{repo_name.lower()}"
        return Observation(
            observation_id=f"obs_ghevent_{event.get('id')}",
            source=self.source_name,
            source_family=self.source_family,
            entity_type="repository_interaction",
            entity_id=f"github:event:{event.get('id')}",
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            occurred_at=_dt(event.get("created_at")),
            value={"event_type": event.get("type"), "payload_action": (event.get("payload") or {}).get("action")},
            sector=sector,
            evidence=evidence_for_payload(event, f"https://github.com/{repo_name}", str(event.get("id"))),
            quality={"temporal_precision": "event", "api_latency_possible": True},
        )
