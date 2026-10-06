from datetime import datetime, timezone
from subprocess import CompletedProcess

import pytest

import src.publish_readme as publisher
from src.publish_readme import (
    AmbiguousPullRequestError,
    PR_TITLE,
    publication_actions,
    select_pull_request,
)


REPOSITORY = "example/project"


def pull_request(
    *,
    title: str = PR_TITLE,
    state: str = "open",
    base: str = "main",
    head: str = "user/update-features-20261006T120000Z",
    repository: str = REPOSITORY,
) -> dict[str, object]:
    return {
        "title": title,
        "state": state,
        "base": {"ref": base},
        "head": {"ref": head, "repo": {"full_name": repository}},
    }


def test_selects_only_exact_open_same_repository_pull_request() -> None:
    expected = pull_request()
    candidates = [
        pull_request(title="Other title"),
        pull_request(state="closed"),
        pull_request(base="release"),
        pull_request(head="someone/update-features-20261006T120000Z"),
        pull_request(repository="fork/project"),
        expected,
    ]

    assert select_pull_request(candidates, REPOSITORY) is expected


def test_select_returns_none_when_no_pull_request_qualifies() -> None:
    assert select_pull_request([pull_request(repository="fork/project")], REPOSITORY) is None


def test_select_rejects_ambiguous_pull_requests() -> None:
    with pytest.raises(AmbiguousPullRequestError):
        select_pull_request([pull_request(), pull_request(head="user/update-features-other")], REPOSITORY)


def test_open_pull_requests_reads_all_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [[{} for _ in range(100)], []]
    endpoints: list[str] = []

    def fake_request(
        token: str,
        repository: str,
        endpoint: str,
        method: str = "GET",
        payload: dict[str, object] | None = None,
    ) -> tuple[object, str | None]:
        endpoints.append(endpoint)
        return responses.pop(0), None

    monkeypatch.setattr(publisher, "_github_request", fake_request)

    assert publisher._open_pull_requests("token", REPOSITORY) == [{} for _ in range(100)]
    assert len(endpoints) == 2
    assert endpoints[0].endswith("page=1")
    assert endpoints[1].endswith("page=2")


def test_timestamped_branch_uses_utc_format() -> None:
    timestamp = datetime(2026, 10, 6, 12, 30, 45, tzinfo=timezone.utc)

    assert publisher._timestamped_branch(timestamp) == "user/update-features-20261006T123045Z"


def test_existing_branch_merges_tested_sha_during_preparation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    def fake_run_git(*arguments: str, check: bool = True) -> CompletedProcess[str]:
        commands.append(arguments)
        return CompletedProcess(["git", *arguments], 0, "", "")

    monkeypatch.setattr(publisher, "_run_git", fake_run_git)

    branch, is_new_branch = publisher._prepare_branch(pull_request(), "event-sha")

    assert branch == "user/update-features-20261006T120000Z"
    assert not is_new_branch
    assert [command[0] for command in commands] == ["fetch", "switch", "merge"]
    assert commands[-1] == ("merge", "--no-edit", "event-sha")


def test_main_merges_existing_branch_before_readme_sync_and_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    def fake_run_git(*arguments: str, check: bool = True) -> CompletedProcess[str]:
        events.append(arguments[0])
        return CompletedProcess(["git", *arguments], 0, "", "")

    def fake_sync_readme(*_args: object) -> bool:
        events.append("sync_readme")
        return True

    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_SHA", "event-sha")
    monkeypatch.setattr(publisher, "_open_pull_requests", lambda *_: [pull_request()])
    monkeypatch.setattr(publisher, "_run_git", fake_run_git)
    monkeypatch.setattr(publisher, "sync_readme", fake_sync_readme)

    assert publisher.main() == 0
    assert events.index("merge") < events.index("sync_readme") < events.index("push")


def test_main_does_not_push_when_existing_branch_merge_conflicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pull = pull_request()
    commands: list[tuple[str, ...]] = []

    def fake_run_git(*arguments: str, check: bool = True) -> CompletedProcess[str]:
        commands.append(arguments)
        return CompletedProcess(
            ["git", *arguments],
            1 if arguments[0] == "merge" else 0,
            "",
            "conflict" if arguments[0] == "merge" else "",
        )

    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_SHA", "event-sha")
    monkeypatch.setattr(publisher, "_open_pull_requests", lambda *_: [pull])
    monkeypatch.setattr(publisher, "_run_git", fake_run_git)

    with pytest.raises(RuntimeError, match="could not merge"):
        publisher.main()

    assert not any(command[0] == "push" for command in commands)


def test_main_pushes_update_before_opening_new_pull_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actions: list[str] = []

    def fake_run_git(*arguments: str, check: bool = True) -> CompletedProcess[str]:
        actions.append(arguments[0])
        return CompletedProcess(["git", *arguments], 0, "", "")

    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_SHA", "event-sha")
    monkeypatch.setattr(publisher, "_open_pull_requests", lambda *_: [])
    monkeypatch.setattr(publisher, "_timestamped_branch", lambda: "user/update-features-new")
    monkeypatch.setattr(publisher, "_run_git", fake_run_git)
    monkeypatch.setattr(publisher, "sync_readme", lambda *_args: True)
    monkeypatch.setattr(
        publisher,
        "_publish_pull_request",
        lambda *_args: actions.append("open_pr"),
    )

    assert publisher.main() == 0
    assert actions.index("push") < actions.index("open_pr")


@pytest.mark.parametrize(
    ("changed", "is_new_branch", "expected"),
    [
        (False, True, ()),
        (False, False, ()),
        (True, False, ("commit", "push")),
        (True, True, ("commit", "push", "open_pr")),
    ],
)
def test_publication_actions_follow_readme_change_and_branch_status(
    changed: bool, is_new_branch: bool, expected: tuple[str, ...]
) -> None:
    assert publication_actions(changed, is_new_branch) == expected