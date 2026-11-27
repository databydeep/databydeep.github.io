"""Benchmark a real serving endpoint using the same 15 held-out prompts."""

import argparse
import json
import time
from pathlib import Path
from core import ROOT, TOOLS, route_model

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("provider", choices=["ollama", "compatible"])
    parser.add_argument("--out", type=Path, default=Path("provider-results.json"))
    args = parser.parse_args()
    prompts = json.loads((ROOT / "routing_data.json").read_text())
    results = []
    for tool in TOOLS:
        for question in prompts[tool]["test"]:
            start = time.monotonic()
            try:
                choice = route_model(question, args.provider)
            except (ValueError, OSError, KeyError, IndexError, TypeError) as error:
                choice = type(error).__name__
            results.append(
                dict(
                    question=question,
                    expected=tool,
                    choice=choice,
                    elapsed_ms=round((time.monotonic() - start) * 1000),
                )
            )
    report = dict(
        provider=args.provider,
        correct=sum(r["choice"] == r["expected"] for r in results),
        total=len(results),
        results=results,
    )
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(report["correct"], "of", report["total"])
