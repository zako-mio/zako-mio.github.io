#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub REST adapter implementing the RepoSource port.

Endpoints / credentials come from configuration (``gh_api_base`` / ``GH_TOKEN``)
so no deploy-specific value is hard-coded here. Errors are mapped to a small
taxonomy; a single repository failure is recorded (repo + reason) and never
silently swallowed.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any, Optional, Protocol, runtime_checkable

from domain.models import RepoMetadata

DEFAULT_API_BASE = "https://api.github.com"


class GitHubAPIError(Exception):
    """Transport-level GitHub error with a classified ``kind``."""

    def __init__(self, status: int, kind: str, message: str, path: str):
        super().__init__(f"{kind} ({status}) for {path}: {message}")
        self.status = status
        self.kind = kind
        self.message = message
        self.path = path


def classify_status(status: int) -> str:
    if status == 401:
        return "unauthorized"
    if status == 403:
        return "forbidden_or_rate_limited"
    if status == 404:
        return "not_found"
    if 500 <= status < 600:
        return "server_error"
    if status == 0:
        return "network_error"
    return "http_error"


@runtime_checkable
class RepoSource(Protocol):
    """Port consumed by the domain use-case (dependency inversion)."""

    failures: list[dict[str, str]]

    def list_repos(self) -> list[RepoMetadata]:  # pragma: no cover - protocol
        ...

    def get_readme(self, name: str) -> str:  # pragma: no cover - protocol
        ...


class GitHubSource:
    """REST implementation of :class:`RepoSource`."""

    def __init__(
        self,
        owner: str,
        api_base: str = DEFAULT_API_BASE,
        token: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.owner = owner
        self.api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
        self.token = token or ""
        self.timeout = timeout
        self.failures: list[dict[str, str]] = []
        if not self.token:
            print(
                "WARNING: GH_TOKEN is not set; falling back to anonymous GitHub "
                "API (60 requests/hour). Set GH_TOKEN to raise the limit.",
                file=sys.stderr,
            )

    # -- low level -----------------------------------------------------------
    def _request(
        self,
        path: str,
        accept: str = "application/vnd.github+json",
        method: str = "GET",
        body: Optional[dict[str, Any]] = None,
    ) -> bytes:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.api_base + path, data=data, method=method)
        request.add_header("Accept", accept)
        request.add_header("X-GitHub-Api-Version", "2022-11-28")
        request.add_header("User-Agent", "zako-mio-hub-generator")
        if self.token:
            request.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:  # pragma: no cover - network path
            kind = classify_status(exc.code)
            raise GitHubAPIError(exc.code, kind, str(exc.reason), path) from exc
        except urllib.error.URLError as exc:  # pragma: no cover - network path
            raise GitHubAPIError(0, "network_error", str(exc.reason), path) from exc

    # -- RepoSource ----------------------------------------------------------
    def list_repos(self) -> list[RepoMetadata]:
        """Paginate ``GET /users/{owner}/repos`` (100 per page)."""
        repos: list[RepoMetadata] = []
        page = 1
        while True:
            path = f"/users/{self.owner}/repos?per_page=100&page={page}"
            chunk = json.loads(self._request(path).decode("utf-8"))
            if not chunk:
                break
            repos.extend(RepoMetadata.from_api(raw) for raw in chunk)
            if len(chunk) < 100:
                break
            page += 1
        return repos

    def get_readme(self, name: str) -> str:
        """Raw README text; a failure is recorded, not raised."""
        path = f"/repos/{self.owner}/{name}/readme"
        try:
            return self._request(path, accept="application/vnd.github.raw").decode(
                "utf-8", "replace"
            )
        except GitHubAPIError as exc:
            self.failures.append({"repo": name, "reason": f"{exc.kind} ({exc.status})"})
            return ""

    # -- admin (XII process) -------------------------------------------------
    def get_repo_topics(self, name: str) -> list[str]:
        payload = json.loads(
            self._request(f"/repos/{self.owner}/{name}/topics").decode("utf-8")
        )
        return list(payload.get("names") or [])

    def set_repo_topics(self, name: str, names: list[str]) -> dict[str, Any]:
        raw = self._request(
            f"/repos/{self.owner}/{name}/topics", method="PUT", body={"names": list(names)}
        )
        return json.loads(raw.decode("utf-8")) if raw else {}
