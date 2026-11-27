import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from api import app, RUNS
from core import investigate

client = TestClient(app)


class InvestigationTests(unittest.TestCase):
    def test_capture(self):
        self.assertEqual(len(RUNS), 10)
        self.assertEqual(sum(len(r["jobs"]) for r in RUNS.values()), 387)

    def test_matrix(self):
        view = investigate(RUNS[45849948162], "matrix")
        self.assertEqual(view["failed_jobs"], 22)
        self.assertEqual([len(g["jobs"]) for g in view["evidence"]], [14, 7, 1])
        self.assertEqual(view["evidence"][0]["label"], "Test without coverage")

    def test_missing_step(self):
        view = investigate(RUNS[45876173299], "unknown")
        self.assertEqual(view["missing_step"], 1)
        self.assertTrue(
            view["evidence"][0]["jobs"][0]["url"].startswith(view["run_url"] + "/job/")
        )

    def test_multiple_steps(self):
        view = investigate(RUNS[45928029546], "matrix")
        self.assertEqual((view["failed_jobs"], len(view["evidence"])), (3, 4))

    def test_api(self):
        self.assertEqual(client.get("/runs/45849948162/tools/matrix").status_code, 200)
        self.assertEqual(client.get("/runs/1/tools/matrix").status_code, 404)
        self.assertEqual(client.get("/runs/45849948162/tools/other").status_code, 422)

    def test_planner_validation(self):
        with patch("api.route_model", return_value="other"):
            self.assertEqual(
                client.post(
                    "/runs/45849948162/ask", json={"question": "group failures"}
                ).status_code,
                503,
            )
        with patch("api.route_model", return_value="matrix"):
            result = client.post(
                "/runs/45849948162/ask", json={"question": "group failures"}
            )
            self.assertEqual(
                result.json()["evidence"][0]["label"], "Test without coverage"
            )

    def test_promotion_gate(self):
        result = client.post(
            "/runs/45849948162/ask",
            json={"question": "group them", "planner": "adapter"},
        )
        self.assertEqual(result.status_code, 409)
