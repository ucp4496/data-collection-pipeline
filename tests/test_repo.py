# tests/test_repo_miner.py

import os
import pandas as pd
import pytest
from datetime import datetime, timedelta
from src.repo_miner import fetch_commits, fetch_issues #, merge_and_summarize

# --- Helpers for dummy GitHub API objects ---

class DummyAuthor:
    def __init__(self, name, email, date):
        self.name = name
        self.email = email
        self.date = date

class DummyCommitCommit:
    def __init__(self, author, message):
        self.author = author
        self.message = message

class DummyCommit:
    def __init__(self, sha, author, email, date, message):
        self.sha = sha
        self.commit = DummyCommitCommit(DummyAuthor(author, email, date), message)

class DummyUser:
    def __init__(self, login):
        self.login = login

class DummyIssue:
    def __init__(self, id_, number, title, user, state, created_at, closed_at, comments, is_pr=False):
        self.id = id_
        self.number = number
        self.title = title
        self.user = DummyUser(user)
        self.state = state
        self.created_at = created_at
        self.closed_at = closed_at
        self.comments = comments
        # attribute only on pull requests
        self.pull_request = DummyUser("pr") if is_pr else None

class DummyRepo:
    def __init__(self, commits, issues):
        self._commits = commits
        self._issues = issues

    def get_commits(self):
        return self._commits

    def get_issues(self, state="all"):
        # filter by state
        if state == "all":
            return self._issues
        return [i for i in self._issues if i.state == state]

class DummyGithub:
    def __init__(self, token):
        assert token == "fake-token"

    def get_repo(self, repo_name):
        # ignore repo_name; return repo set in test fixture
        return self._repo

@pytest.fixture(autouse=True)
def patch_env_and_github(monkeypatch):
    # Set fake token
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    # Patch Github class
    monkeypatch.setattr("src.repo_miner.Github", lambda *args, **kwargs: gh_instance)

# Helper global placeholder
gh_instance = DummyGithub("fake-token")

# --- Tests for fetch_commits ---
# An example test case
def test_fetch_commits_basic(monkeypatch):
    # Setup dummy commits
    now = datetime.now()
    commits = [
        DummyCommit("sha1", "Alice", "a@example.com", now, "Initial commit\nDetails"),
        DummyCommit("sha2", "Bob", "b@example.com", now - timedelta(days=1), "Bug fix")
    ]
    gh_instance._repo = DummyRepo(commits, [])
    df = fetch_commits("any/repo")
    assert list(df.columns) == ["sha", "author", "email", "date", "message"]
    assert len(df) == 2
    assert df.iloc[0]["message"] == "Initial commit"

def test_fetch_commits_limit(monkeypatch):
    # More commits than max_commits
    testytime = datetime.now()
    commits = [
        DummyCommit(f"sha{i}", f"Author{i}", f"a{i}@example.com", testytime, f"Commit {i}")
        for i in range(22)
    ]
    gh_instance._repo = DummyRepo(commits, [])
    df = fetch_commits("any/repo", max_commits=10)
    assert len(df) == 10

def test_fetch_commits_empty(monkeypatch):
    gh_instance._repo = DummyRepo([], [])
    df = fetch_commits("any/repo")
    assert df.empty
    assert list(df.columns) == ["sha", "author", "email", "date", "message"]

def test_fetch_issues_basic(monkeypatch):
    now = datetime.now()
    issues = [
        DummyIssue(1, 101, "Issue A", "alice", "open", now, None, 0),
        DummyIssue(2, 102, "Issue B", "bob", "closed", now - timedelta(days=2), now, 2)
    ]
    gh_instance._repo = DummyRepo([], issues)
    df = fetch_issues("any/repo", state="all")
    assert {"id", "number", "title", "user", "state", "created_at", "closed_at", "comments"}.issubset(df.columns)
    assert len(df) == 2

    # Check date normalization
    created_str = df.iloc[0]["created_at"]
    closed_str = df.iloc[1]["closed_at"]

    assert isinstance(created_str, str) and "T" in created_str
    assert isinstance(closed_str, str) and "T" in closed_str

def test_fetch_issues_excludes_prs(monkeypatch):
    now = datetime.now()
    issues = [
        DummyIssue(1, 101, "Regular Issue", "alice", "open", now, None, 0),
        DummyIssue(2, 102, "Looks like PR", "bob", "open", now, None, 0, is_pr=True)
    ]
    gh_instance._repo = DummyRepo([], issues)
    df = fetch_issues("any/repo", state="all")

    assert len(df) == 1

def test_fetch_issues_dates_are_iso8601(monkeypatch):
    now = datetime(2025, 9, 25, 12, 30, 45)
    closed = datetime(2025, 9, 26, 13, 15, 0)

    issues = [
        DummyIssue(1, 101, "Issue A", "alice", "closed", now, closed, 5)
    ]
    gh_instance._repo = DummyRepo([], issues)
    df = fetch_issues("any/repo", state="all")

    created_str = df.iloc[0]["created_at"]
    closed_str = df.iloc[0]["closed_at"]

    assert created_str == "2025-09-25T12:30:45"
    assert closed_str == "2025-09-26T13:15:00"


def test_fetch_issues_open_duration_days(monkeypatch):
    created = datetime(2025, 9, 20, 10, 0, 0)
    closed = datetime(2025, 9, 25, 10, 0, 0)
    issues = [
        DummyIssue(1, 101, "Closed Issue", "alice", "closed", created, closed, 3)
    ]
    gh_instance._repo = DummyRepo([], issues)
    df = fetch_issues("any/repo", state="all")

    duration = df.iloc[0]["open_duration_days"]
    assert duration == 5

#LLM usage: point me to the documentation, help with explanation of it, basic debugging assistance, giving me random data ideas