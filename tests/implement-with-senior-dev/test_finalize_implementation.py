import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "implement-with-senior-dev" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _plan_utils import bundle_digest  # noqa: E402
from check_implementation import validate_bundle  # noqa: E402
from finalize_implementation import main as finalize_main  # noqa: E402
from test_check_implementation import completed_run  # noqa: E402


def test_finalize_stamps_valid_bundle_receipt(tmp_path: Path) -> None:
    repo, plan_path, output, bundle = completed_run(tmp_path)
    output.write_text(json.dumps(bundle), encoding="utf-8")

    code = finalize_main([
        "--repo-root", str(repo),
        "--plan", str(plan_path),
        str(output),
    ])

    assert code == 0
    finalized = json.loads(output.read_text(encoding="utf-8"))
    assert "validation_receipt" in finalized
    assert finalized["validation_receipt"]["version"] == 1
    assert finalized["validation_receipt"]["sha256"] == bundle_digest(bundle)
    assert validate_bundle(finalized, plan_path.read_text(encoding="utf-8"), repo, require_receipt=True) == []


def test_finalize_rejects_invalid_bundle(tmp_path: Path) -> None:
    repo, plan_path, output, bundle = completed_run(tmp_path)
    bundle.pop("validation_receipt", None)
    bundle["unresolved_changes"] = ["CH-1"]
    output.write_text(json.dumps(bundle), encoding="utf-8")

    code = finalize_main([
        "--repo-root", str(repo),
        "--plan", str(plan_path),
        str(output),
    ])

    assert code == 1
    unfinalized = json.loads(output.read_text(encoding="utf-8"))
    assert "validation_receipt" not in unfinalized


def test_tampered_bundle_fails_receipt_validation(tmp_path: Path) -> None:
    repo, plan_path, output, bundle = completed_run(tmp_path)
    output.write_text(json.dumps(bundle), encoding="utf-8")
    finalize_main(["--repo-root", str(repo), "--plan", str(plan_path), str(output)])

    stamped = json.loads(output.read_text(encoding="utf-8"))
    stamped["report"]["summary"] = "Tampered summary after finalization."
    output.write_text(json.dumps(stamped), encoding="utf-8")

    diagnostics = validate_bundle(stamped, plan_path.read_text(encoding="utf-8"), repo, require_receipt=True)
    assert any(diag.code == "bundle.receipt.stale" for diag in diagnostics)
