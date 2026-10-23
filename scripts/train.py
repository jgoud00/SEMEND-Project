import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.ml import train  # noqa: E402

if __name__ == "__main__":
    report = train()
    print(json.dumps({"trials": report["trials"], "windows": report["windows"], "records": [{k: r[k] for k in ["model", "modality", "accuracy", "f1_macro"]} for r in report["records"]]}, indent=2))
