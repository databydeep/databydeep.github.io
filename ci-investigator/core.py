import json
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen
import os

ROOT = Path(__file__).resolve().parent
TOOLS = ("failures", "matrix", "unknown")
GUIDE = "failures lists failed jobs; matrix groups matching failed step names; unknown lists failures without step evidence."


def route_model(question, provider):
    prompt = "Pick one tool. " + GUIDE + ' Respond only with {"tool":"name"}.'
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": question},
    ]
    headers = {"Content-Type": "application/json"}
    if provider == "ollama":
        url = (
            os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/api/chat"
        )
        payload = dict(
            model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            messages=messages,
            stream=False,
            think=False,
            format="json",
            options={"temperature": 0},
        )
    else:
        url = os.environ["MODEL_BASE_URL"].rstrip("/") + "/chat/completions"
        payload = dict(
            model=os.environ["MODEL_NAME"],
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=256,
        )
        if os.getenv("MODEL_API_KEY"):
            headers["Authorization"] = "Bearer " + os.environ["MODEL_API_KEY"]
    req = Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urlopen(req, timeout=45) as response:
        output = json.load(response)
    msg = output["message"] if provider == "ollama" else output["choices"][0]["message"]
    return json.loads(msg["content"])["tool"]


def investigate(run, tool):
    if tool not in TOOLS:
        raise ValueError("Unknown investigation tool")
    failed = [
        j
        for j in run["jobs"]
        if j["result"] in {"failure", "timed_out", "startup_failure"}
    ]
    url = f"https://github.com/{run['repo']}/actions/runs/{run['run']}"
    groups = defaultdict(list)
    for job in failed:
        ref = {"job": job["job"], "url": url + "/job/" + str(job["id"])}
        if tool == "unknown":
            if not job["steps"]:
                groups["No failed step reported"].append(ref)
        elif tool == "failures":
            groups[job["job"]].append({**ref, "steps": job["steps"]})
        else:
            for step in dict.fromkeys(job["steps"]):
                groups[step].append(ref)
    ordered = sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    return dict(
        tool=tool,
        run_url=url,
        attempt=run["attempt"],
        jobs=len(run["jobs"]),
        failed_jobs=len(failed),
        missing_step=sum(not j["steps"] for j in failed),
        evidence=[{"label": label, "jobs": jobs} for label, jobs in ordered],
    )
