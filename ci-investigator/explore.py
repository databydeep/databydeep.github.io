"""Optional local PandasAI analysis of numeric aggregate data only."""

import json
import os
import pandasai as pai
from pandasai_litellm.litellm import LiteLLM
from core import ROOT, investigate

rows = []
for run in json.loads((ROOT / "runs.json").read_text()):
    view = investigate(run, "matrix")
    rows.append(
        {
            "run_id": str(run["run"]),
            "jobs": view["jobs"],
            "failed_jobs": view["failed_jobs"],
            "distinct_failed_steps": len(view["evidence"]),
            "missing_step": view["missing_step"],
        }
    )
model = LiteLLM(
    model="ollama/" + os.getenv("OLLAMA_MODEL", "qwen3:8b"),
    api_base=os.getenv("OLLAMA_URL", "http://localhost:11434"),
    temperature=0,
)
pai.config.set({"llm": model})
print(
    pai.DataFrame(rows).chat(
        "Which run had the most failed jobs? Return the run_id and failed_jobs."
    )
)
