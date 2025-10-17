#!/usr/bin/env python3
"""
repo_miner.py

A command-line tool to:
  1) Fetch and normalize commit data from GitHub
  2) Fetch and normalize issue data from GitHub
  3) Merge data and print summary metrics

Sub-commands:
  - fetch-commits
  - fetch-issues
  - summarize
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

def merge_and_summarize(commits_df: pd.DataFrame, issues_df: pd.DataFrame) -> None:
    """
    Takes two DataFrames (commits and issues) and prints:
      - Top 5 committers by commit count
      - Issue close rate (closed/total)
      - Average open duration for closed issues (in days)
    """
    # Copy to avoid modifying original data
    commits = commits_df.copy()
    issues  = issues_df.copy()

    # 1) Normalize date/time columns to pandas datetime
    commits['date']      = pd.to_datetime(commits['date'], errors='coerce')
    issues['created_at'] = pd.to_datetime(issues['created_at'], errors='coerce')
    issues['closed_at'] = pd.to_datetime(issues['closed_at'], errors='coerce')

    # 2) Top 5 committers
    print("Top 5 committers:")
    committer_counts = commits['author'].value_counts()[0:5]
    for author, count in committer_counts.items():
        print(f"{author}: {count} commits")
    print()

    # 3) Calculate issue close rate
    total_issues = len(issues)
    closed_issues = len(issues[issues['state'] == 'closed'])

    close_rate = closed_issues / total_issues if total_issues > 0 else 0

    print(f"Issue close rate: {close_rate:.2f}")
    print()

    # 4) Compute average open duration (days) for closed issues
    closed_df = issues[issues['state'] == 'closed'].copy()
    closed_df['open_duration_days'] = (closed_df['closed_at'] - closed_df['created_at']).dt.days

    avg_open_duration = closed_df['open_duration_days'].mean() if not closed_df.empty else 0
    print(f"Avg. issue open duration: {avg_open_duration} days")


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

    c3 = subparsers.add_parser("summarize", help="Summarize commits and issues")
    c3.add_argument("--commits", required=True, help="Path to commits CSV file")
    c3.add_argument("--issues",  required=True, help="Path to issues CSV file")

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

    if args.command == "summarize":
        # Read CSVs into DataFrames
        commits_df = pd.read_csv(args.commits)
        issues_df  = pd.read_csv(args.issues)
        # Generate and print the summary
        merge_and_summarize(commits_df, issues_df)

if __name__ == "__main__":
    main()

#LLM usage: help me find/understand github python documentation