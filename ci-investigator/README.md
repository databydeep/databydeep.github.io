# CI Failure Investigator

Start with [the interactive evidence viewer](./index.html) or run the local API. In the included pytest run, 22 failed jobs share three failed-step names. Open the 14 jobs grouped under “Test without coverage” to compare their original logs. The pandas ASAN run illustrates a different outcome: GitHub reports failure but supplies no failed step.

## Evidence and scope

The 10 captured run attempts contain 387 jobs across pytest, pandas, DuckDB, Ruff and pip. The capture stores GitHub job and step metadata. Each result links to the original GitHub job, where access to logs depends on GitHub permissions and retention. Shared step names are a way to prioritise inspection. A root-cause determination requires reading the logs.

Three bounded tools list failed jobs, group matching step names and surface missing evidence. An optional model selects a tool from a natural-language request. Results and links come from the captured evidence. An invalid or unavailable model returns a visible error. The named-tool API remains available. The browser uses the captured data and runs without a model server or credentials.

## Run on a Mac with Python 3.12 and uv

From the ci-investigator directory:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python -m unittest -v
uvicorn api:app --port 8010
```

Open http://localhost:8010/docs. Try GET /runs/45849948162/tools/matrix. In another terminal, with Ollama running and qwen3:8b installed, ask the same question:

```bash
curl -s http://localhost:8010/runs/45849948162/ask -H 'Content-Type: application/json' -d '{"question":"Do the same steps fail across multiple runners?","planner":"ollama"}'
```

Run the 15-prompt benchmark with `python evaluate_provider.py ollama`. Check the selected tool and latency for each question. Start the browser demo locally with `python -m http.server 8000` and open http://localhost:8000.

## Model experiment

The PyTorch experiment uses Hugging Face SmolLM2-135M-Instruct at a pinned revision. LoRA updates the query and value projection adapters. The objective compares three label-token logits. There are 36 authored training prompts and 15 held-out paraphrases. These measure tool selection within this small English prompt set. They do not measure incident resolution, time saved or performance on new teams.

The base model routed 5/15 correctly. The tuned adapter routed 3/15 correctly. The API blocks adapter selection while its held-out score is at or below the baseline. The released demo uses named tools, and the Ollama endpoint is available for local benchmarking. Compare the per-prompt predictions in routing_scores.json against routing_data.json.

```bash
uv pip install -r requirements-training.txt
python tune.py
```

The script downloads the base model and writes local adapter weights and a new routing_scores.json. It uses Apple MPS when available. The recorded experiment ran on CPU; results can vary with the device.

## Serving and analytics

To evaluate the same Qwen3-8B family on a team-operated OpenAI-compatible endpoint, set MODEL_BASE_URL (including /v1), MODEL_NAME and optionally MODEL_API_KEY in the API process. Select compatible as the planner. Run `python evaluate_provider.py compatible` before comparing environments. Record the served checkpoint, precision, quantisation, accuracy and latency alongside the local results. The local Ollama and hosted paths require a separately running model server.

For optional PandasAI exploration, create a separate environment and install `pandasai>=3,<4` and `pandasai-litellm`. Run `python explore.py` with Ollama running. This local experiment asks one fixed question over numerical run summaries. Its answer can be checked against the 22 failed jobs in run 45849948162.

Refresh or add evidence with `python capture.py pytest-dev/pytest 45849948162 next-run.json`. Inspect its attempt number before adding it to runs.json. The API loads snapshots on startup. The web demo starts with recorded attempts. Select “Load latest failed run” to fetch fresh public job metadata directly from GitHub. Rate limits and API outages leave the selected run available. The API follows a selected tool with an evidence-gap check when needed, with at most two tool calls.
