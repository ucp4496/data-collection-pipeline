#!/usr/bin/env python3
"""
repo_miner.py

A command-line tool to:
  1) Fetch and normalize commit data from GitHub

Sub-commands:
  - fetch-commits
"""

import os
import argparse
import pandas as pd
from github import Github
from github import Auth

def fetch_commits(repo_name: str, max_commits: int = None) -> pd.DataFrame:
    """
    Fetch up to `max_commits` from the specified GitHub repository.
    Returns a DataFrame with columns: sha, author, email, date, message.
    """
    # 1) Read GitHub token from environment
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN in environment")

    # 2) Initialize GitHub client and get the repo
    git = Github(auth=Auth.Token(token))
    repo = git.get_repo(repo_name)

    # 3) Fetch commit objects (paginated by PyGitHub)
    commits = repo.get_commits()
    records = []

    # 4) Normalize each commit into a record dict
    for i, commit in enumerate(commits):
        if max_commits is not None and i >= max_commits:
            break
        print(f"DEBUG commit {i}: {commit.sha}")

        commit_data = commit.commit
        author = None
        email = None
        date = None

        if commit_data.author:
            author = commit_data.author.name
            email = commit_data.author.email
            date = commit_data.author.date.isoformat()

        message = ""
        if commit_data.message:
            message = commit_data.message.splitlines()[0]

        records.append({
            "sha": commit.sha,
            "author": author,
            "email": email,
            "date": date,
            "message": message
        })

    # 5) Build DataFrame from records
    return pd.DataFrame(records, columns=["sha", "author", "email", "date", "message"])
    
def fetch_issues(repo_name: str, state: str = "all", max_issues: int = None) -> pd.DataFrame:
    """
    Fetch up to `max_issues` from the specified GitHub repository (issues only).
    Returns a DataFrame with columns: id, number, title, user, state, created_at, closed_at, comments.
    """
    # 1) Read GitHub token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN in environment")

    # 2) Initialize client and get the repo
    git = Github(auth=Auth.Token(token))
    repo = git.get_repo(repo_name)

    # 3) Fetch issues, filtered by state ('all', 'open', 'closed')
    issues = repo.get_issues(state=state)

    # 4) Normalize each issue (skip PRs)
    records = []
    for idx, issue in enumerate(issues):
        if max_issues and idx >= max_issues:
            break
        # Skip pull requests
        if issue.pull_request is not None:
            continue

        #normalizing date stuff
        created_at = issue.created_at.isoformat() if issue.created_at else None
        closed_at = issue.closed_at.isoformat() if issue.closed_at else None

        #new column stuff
        open_duration = None
        if issue.closed_at and issue.created_at:
            open_time = issue.closed_at - issue.created_at
            open_duration = open_time.days

        # Append records
        records.append({
            "id": issue.id,
            "number": issue.number,
            "title": issue.title,
            "user": issue.user.login if issue.user else None,
            "state": issue.state,
            "created_at": created_at,
            "closed_at": closed_at,
            "comments": issue.comments,
            "open_duration_days": open_duration
        })

    # 5) Build DataFrame
    return pd.DataFrame(records, columns=["id", "number", "title", "user", "state", "created_at", "closed_at", "comments", "open_duration_days"])

def main():
    """
    Parse command-line arguments and dispatch to sub-commands.
    """
    parser = argparse.ArgumentParser(
        prog="repo_miner",
        description="Fetch GitHub commits/issues and summarize them"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Sub-command: fetch-commits
    c1 = subparsers.add_parser("fetch-commits", help="Fetch commits and save to CSV")
    c1.add_argument("--repo", required=True, help="Repository in owner/repo format")
    c1.add_argument("--max",  type=int, dest="max_commits",
                    help="Max number of commits to fetch")
    c1.add_argument("--out",  required=True, help="Path to output commits CSV")

    # Sub-command: fetch-issues
    c2 = subparsers.add_parser("fetch-issues", help="Fetch issues and save to CSV")
    c2.add_argument("--repo",  required=True, help="Repository in owner/repo format")
    c2.add_argument("--state", choices=["all","open","closed"], default="all",
                    help="Filter issues by state")
    c2.add_argument("--max",   type=int, dest="max_issues",
                    help="Max number of issues to fetch")
    c2.add_argument("--out",   required=True, help="Path to output issues CSV")

    # Dispatch based on selected command
    args = parser.parse_args()
    
    if args.command == "fetch-commits":
        df = fetch_commits(args.repo, args.max_commits)
        df.to_csv(args.out, index=False)
        print(f"Saved {len(df)} commits to {args.out}")

    elif args.command == "fetch-issues":
        df = fetch_issues(args.repo, args.state, args.max_issues)
        df.to_csv(args.out, index=False)
        print(f"Saved {len(df)} issues to {args.out}")

if __name__ == "__main__":
    main()

#LLM usage: help me find/understand github python documentation