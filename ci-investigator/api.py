import json
from functools import lru_cache
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from core import ROOT, TOOLS, investigate, route_model

app = FastAPI(title="CI Failure Investigator")
RUNS = {r["run"]: r for r in json.loads((ROOT / "runs.json").read_text())}


class Query(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    planner: Literal["ollama", "compatible", "adapter"] = "ollama"


@lru_cache(maxsize=1)
def adapter():
    from tune import Router

    return Router.from_adapter()


@app.post("/runs/{run_id}/ask")
def ask(run_id: int, query: Query):
    if run_id not in RUNS:
        raise HTTPException(404, "Unknown snapshot")
    if query.planner == "adapter":
        report = json.loads((ROOT / "routing_scores.json").read_text())
        if report["tuned"]["correct"] <= report["base"]["correct"]:
            raise HTTPException(
                409,
                "Adapter failed the held-out comparison. Use a named tool or another planner.",
            )
    try:
        pick = (
            route_model(query.question, query.planner)
            if query.planner != "adapter"
            else adapter().predict([query.question])[0]
        )
        if pick not in TOOLS:
            raise ValueError("Invalid selection")
    except (
        OSError,
        RuntimeError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        ImportError,
    ) as err:
        raise HTTPException(
            503,
            "Planner unavailable or invalid response. Use the named tools endpoint.",
        ) from err
    snapshot = RUNS[run_id]
    result = investigate(snapshot, pick)
    trace = [pick]
    if result["missing_step"] and pick != "unknown":
        result["evidence_gaps"] = investigate(snapshot, "unknown")["evidence"]
        trace.append("unknown")
    return {"planner": query.planner, "tool_trace": trace, **result}


@app.get("/runs/{run_id}/tools/{tool}")
def run_tool(run_id: int, tool: Literal["failures", "matrix", "unknown"]):
    if run_id not in RUNS:
        raise HTTPException(404, "Unknown snapshot")
    return investigate(RUNS[run_id], tool)
