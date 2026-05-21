import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_meta_harness_benchmarks_script_outputs_valid_json() -> None:
    script = REPO_ROOT / "scripts" / "export_meta_harness_benchmarks.py"
    env = dict(os.environ)
    src = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else src + os.pathsep + env["PYTHONPATH"]

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["meta"]["entrypoint"] == "MetaFramework.execute"
    assert data["benchmark_smoke"]["passed"] is True
    assert data["value_proof"]["benchmark_id"] == "meta_harness.value_proof.v1"
    assert data["value_proof"]["passed"] is True
