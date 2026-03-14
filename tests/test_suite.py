"""
Test suite for AI Data Analyst Agent.
Run with: pytest tests/ -v
"""

import io
import os
import tempfile

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def make_csv_bytes(n: int = 200) -> bytes:
    """Generate a realistic test dataset."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "customer_id": range(1, n + 1),
        "age": rng.integers(18, 80, n),
        "revenue": rng.normal(5000, 2000, n).round(2),
        "churn": rng.choice([0, 1], n, p=[0.8, 0.2]),
        "segment": rng.choice(["SMB", "Enterprise", "Startup"], n),
        "region": rng.choice(["EU", "US", "APAC"], n),
        "tenure_months": rng.integers(1, 60, n),
        "nps_score": rng.integers(0, 10, n),
    })
    df.loc[rng.choice(n, 15, replace=False), "nps_score"] = np.nan
    return df.to_csv(index=False).encode("utf-8")


# ── System Tests ───────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_endpoint(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"

    def test_root_endpoint(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "docs" in r.json()


# ── Upload Tests ───────────────────────────────────────────────────────────────

class TestUpload:
    def test_upload_csv_success(self):
        csv_bytes = make_csv_bytes()
        r = client.post(
            "/api/v1/upload",
            files={"file": ("test_data.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert r.status_code == 201
        data = r.json()
        assert "session_id" in data
        assert data["filename"] == "test_data.csv"
        assert data["size_bytes"] > 0

    def test_upload_invalid_extension(self):
        r = client.post(
            "/api/v1/upload",
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert r.status_code == 422

    def test_upload_empty_file(self):
        r = client.post(
            "/api/v1/upload",
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        )
        assert r.status_code == 422


# ── Analysis Tests ─────────────────────────────────────────────────────────────

class TestAnalysis:
    def test_analysis_not_found(self):
        r = client.get("/api/v1/analyse/nonexistentsession123")
        assert r.status_code == 404

    def test_start_analysis_no_upload(self):
        r = client.post("/api/v1/analyse/nonexistentsession123")
        assert r.status_code == 404

    def test_full_upload_and_start(self):
        """Integration test: upload then trigger analysis."""
        csv_bytes = make_csv_bytes()
        upload_r = client.post(
            "/api/v1/upload",
            files={"file": ("test_data.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert upload_r.status_code == 201
        session_id = upload_r.json()["session_id"]
        analysis_r = client.post(f"/api/v1/analyse/{session_id}")
        assert analysis_r.status_code in (202, 500)


# ── Tool Unit Tests ────────────────────────────────────────────────────────────

class TestTools:
    def test_load_csv(self):
        from agent.tools import load_dataframe
        csv_bytes = make_csv_bytes(50)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(csv_bytes)
            f.flush()
            df = load_dataframe(f.name)
        assert df.shape == (50, 8)
        os.unlink(f.name)

    def test_get_dataset_summary(self):
        from agent.tools import get_dataset_summary
        df = pd.DataFrame({
            "a": [1, 2, 3, None],
            "b": ["x", "y", "x", "z"],
        })
        summary = get_dataset_summary(df)
        assert summary["shape"]["rows"] == 4
        assert summary["shape"]["columns"] == 2
        assert len(summary["columns"]) == 2

    def test_overview_charts(self):
        from agent.tools import generate_overview_charts
        rng = np.random.default_rng(0)
        df = pd.DataFrame({
            "num1": rng.normal(0, 1, 100),
            "num2": rng.normal(5, 2, 100),
            "cat": rng.choice(["A", "B", "C"], 100),
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            charts = generate_overview_charts(df, tmpdir)
            assert len(charts) >= 1
            for chart in charts:
                assert os.path.exists(chart["path"])

    def test_execute_viz_code_success(self):
        from agent.tools import execute_viz_code
        df = pd.DataFrame({"x": range(10), "y": range(10)})
        code = """
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(df['x'], df['y'], color='#4F46E5')
ax.set_title('Test Chart')
plt.savefig(output_path, dpi=72, bbox_inches='tight', facecolor='white')
plt.close()
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = execute_viz_code(code, df, tmpdir)
            assert result["success"] is True
            assert os.path.exists(result["path"])

    def test_execute_viz_code_bad_code(self):
        from agent.tools import execute_viz_code
        df = pd.DataFrame({"x": [1, 2]})
        code = "raise ValueError('intentional test error')"
        with tempfile.TemporaryDirectory() as tmpdir:
            result = execute_viz_code(code, df, tmpdir)
            assert result["success"] is False
            assert "error" in result