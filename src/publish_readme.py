"""Prepare and publish the generated README on a documentation-sync branch."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.sync_readme import DEFAULT_README, sync_readme


PR_TITLE = "[docs-sync] Update README features"
BASE_BRANCH = "main"
HEAD_PREFIX = "user/update-features-"
GITHUB_API = "https://api.github.com"


class AmbiguousPullRequestError(RuntimeError):
    """Raised when more than one open PR satisfies the reuse rules."""


def select_pull_request(
    pull_requests: list[dict[str, object]], repository: str
) -> dict[str, object] | None:
    matches = [
        pull_request
        for pull_request in pull_requests
        if pull_request.get("state") == "open"
        and pull_request.get("title") == PR_TITLE
        and isinstance(pull_request.get("base"), dict)
        and pull_request["base"].get("ref") == BASE_BRANCH
        and isinstance(pull_request.get("head"), dict)
        and pull_request["head"].get("ref", "").startswith(HEAD_PREFIX)
        and isinstance(pull_request["head"].get("repo"), dict)
        and pull_request["head"]["repo"].get("full_name") == repository
    ]
    if len(matches) > 1:
        raise AmbiguousPullRequestError(
            "multiple open pull requests match the README sync rules"
        )
    return matches[0] if matches else None


def publication_actions(readme_changed: bool, is_new_branch: bool) -> tuple[str, ...]:
    if not readme_changed:
        return ()
    actions = ("commit", "push")
    return actions + (("open_pr",) if is_new_branch else ())


def _github_request(
    token: str,
    repository: str,
    endpoint: str,
    method: str = "GET",
    payload: dict[str, object] | None = None,
) -> tuple[object, str | None]:
    request_data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{GITHUB_API}/repos/{repository}/{endpoint}",
        data=request_data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request) as response:
            body = json.loads(response.read())
            return body, response.headers.get("Link")
    except (HTTPError, URLError) as error:
        status = getattr(error, "code", None)
        detail = f" (HTTP {status})" if status is not None else ""
        raise RuntimeError(f"GitHub API request failed{detail}") from None


def _open_pull_requests(token: str, repository: str) -> list[dict[str, object]]:
    pull_requests: list[dict[str, object]] = []
    page = 1
    while True:
        response, _ = _github_request(
            token,
            repository,
            f"pulls?state=open&per_page=100&page={page}",
        )
        if not isinstance(response, list):
            raise RuntimeError("GitHub returned an invalid pull request list")
        pull_requests.extend(item for item in response if isinstance(item, dict))
        if len(response) < 100:
            return pull_requests
        page += 1


def _run_git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode:
        raise RuntimeError(f"git {arguments[0]} failed")
    return result


def _timestamped_branch(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    return f"{HEAD_PREFIX}{timestamp}"


def _prepare_branch(
    pull_request: dict[str, object] | None,
    event_sha: str,
) -> tuple[str, bool]:
    if pull_request is None:
        branch = _timestamped_branch()
        _run_git("switch", "--create", branch, event_sha)
        return branch, True

    head = pull_request["head"]
    branch = head["ref"]
    _run_git(
        "fetch",
        "origin",
        f"refs/heads/{branch}:refs/remotes/origin/{branch}",
    )
    _run_git("switch", "--force-create", branch, f"refs/remotes/origin/{branch}")
    merge = _run_git("merge", "--no-edit", event_sha, check=False)
    if merge.returncode:
        raise RuntimeError("could not merge the tested main commit; no changes were pushed")
    return branch, False


def _publish_pull_request(token: str, repository: str, branch: str) -> None:
    _github_request(
        token,
        repository,
        "pulls",
        method="POST",
        payload={
            "title": PR_TITLE,
            "head": branch,
            "base": BASE_BRANCH,
            "body": "Updates the README feature list from `src/features.py`.",
        },
    )


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    event_sha = os.environ.get("GITHUB_SHA", "")
    if not token or not repository or not event_sha:
        raise RuntimeError("GITHUB_TOKEN, GITHUB_REPOSITORY, and GITHUB_SHA are required")

    from src.features import features

    feature_names = features()
    pull_request = select_pull_request(_open_pull_requests(token, repository), repository)
    branch, is_new_branch = _prepare_branch(pull_request, event_sha)
    changed = sync_readme(DEFAULT_README, feature_names)
    actions = publication_actions(changed, is_new_branch)
    if not actions:
        print("README already up to date; nothing was published")
        return 0

    _run_git("add", "--", DEFAULT_README.name)
    _run_git(
        "-c",
        "user.name=github-actions[bot]",
        "-c",
        "user.email=41898282+github-actions[bot]@users.noreply.github.com",
        "commit",
        "-m",
        "docs-sync: update README features",
    )
    _run_git("push", "origin", f"HEAD:refs/heads/{branch}")
    if "open_pr" in actions:
        _publish_pull_request(token, repository, branch)
    print("README update published")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AmbiguousPullRequestError, RuntimeError, ValueError) as error:
        print(f"README publication failed: {error}", file=sys.stderr)
        raise SystemExit(1)