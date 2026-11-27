"""Capture only public job and step metadata for reproducible investigation."""

import argparse
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

REPOS = {
    "duckdb/duckdb",
    "pandas-dev/pandas",
    "pytest-dev/pytest",
    "astral-sh/ruff",
    "pypa/pip",
}


def fetch(url):
    with urlopen(
        Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "ci-evidence-investigator",
            },
        ),
        timeout=20,
    ) as response:
        return json.load(response)


def capture(repo, run):
    if repo not in REPOS or not re.fullmatch(r"[0-9]{1,16}", str(run)):
        raise ValueError("Choose a supported public repository and numeric run ID")
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run}"
    meta = fetch(url)
    attempt = meta["run_attempt"]
    jobs = []
    for page in range(1, 11):
        batch = fetch(f"{url}/attempts/{attempt}/jobs?per_page=100&page={page}")
        for j in batch["jobs"]:
            jobs.append(
                dict(
                    job=j["name"],
                    id=j["id"],
                    result=j["conclusion"],
                    steps=[
                        s["name"]
                        for s in j.get("steps", [])
                        if s["conclusion"] == "failure"
                    ],
                )
            )
        if len(jobs) >= batch["total_count"]:
            break
    else:
        raise ValueError("Run exceeds capture limit of 1,000 jobs")
    return dict(
        repo=repo, run=int(run), attempt=attempt, workflow=meta["name"], jobs=jobs
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("repo", choices=sorted(REPOS))
    p.add_argument("run", type=int)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    a.output.write_text(json.dumps(capture(a.repo, a.run), indent=2) + "\n")
