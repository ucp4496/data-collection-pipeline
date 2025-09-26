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

    args = parser.parse_args()

    # Dispatch based on selected command
    if args.command == "fetch-commits":
        df = fetch_commits(args.repo, args.max_commits)
        df.to_csv(args.out, index=False)
        print(f"Saved {len(df)} commits to {args.out}")

if __name__ == "__main__":
    main()

#LLM usage: help me find/understand github python documentation