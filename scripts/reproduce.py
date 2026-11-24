"""Rebuild the recorded-data paper offline; this command never collects DNS data."""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def run(command, root, log):
    display = ["." if str(part) == str(root) else str(part).replace(str(root) + "\\", "").replace(str(root) + "/", "") for part in command]
    display[0] = Path(display[0]).name
    line = "\n$ " + subprocess.list2cmdline(display) + "\n"
    print(line, end="", flush=True)
    log.write(line); log.flush()
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    process = subprocess.Popen([str(p) for p in command], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=environment)
    workspace_prefixes = (str(root) + "\\", root.as_posix() + "/", json.dumps(str(root))[1:-1] + "\\\\")
    for line in process.stdout:
        for prefix in workspace_prefixes:
            line = line.replace(prefix, "")
        print(line, end="", flush=True)
        log.write(line); log.flush()
    code = process.wait()
    if code:
        raise RuntimeError(f"Step failed with exit code {code}: {display[1] if len(display)>1 else display[0]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--node", default=shutil.which("node"), help="Node.js executable for the offline wire-parser tests")
    parser.add_argument("--skip-paper", action="store_true", help="Keep the existing paper while regenerating analysis and figures")
    args = parser.parse_args()
    root = args.root.resolve()
    if not args.node:
        parser.error("Node.js was not found; install Node.js 22+ or pass --node PATH")
    evidence = root / "docs/evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    log_path = evidence / "verification.log"
    with log_path.open("w", encoding="utf-8") as log:
        versions = {name: importlib.metadata.version(name) for name in ("numpy", "reportlab", "matplotlib")}
        header = json.dumps({"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "python": sys.version.split()[0], "packages": versions, "mode": "offline reproduction of recorded observations; no network measurements", "command_paths": "Paths under the working directory are displayed relative to the project in commands and captured output"}, indent=2) + "\n"
        print(header, end=""); log.write(header)
        run([sys.executable, root / "scripts/validate_package.py", "--raw-only"], root, log)
        run([args.node, "--version"], root, log)
        run([args.node, root / "tests/test_dns.mjs"], root, log)
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], root, log)
        for data, result in ((root / "data", root / "results"), (root / "data/replication-2026-11-19", root / "results/replication-2026-11-19")):
            if not data.exists():
                continue
            env = json.loads((data / "environment.json").read_text(encoding="utf-8-sig"))
            if env.get("status") != "complete":
                raise RuntimeError(f"Refusing to analyze an incomplete collection: {data.relative_to(root)}")
            run([sys.executable, root / "scripts/analyze.py", "--dns", data / "dns_raw.jsonl", "--pages", data / "pages.jsonl", "--page-dns", data / "page-dns.jsonl", "--out", result, "--expected-windows", str(env["windows"]), "--expected-reps", str(env["reps"]), "--strict"], root, log)
        for script in (
            "robustness.py", "plot_results.py", "control_analysis.py", "plot_control_analysis.py",
            "browser_phases.py", "analyze_loopback.py", "session_analysis.py", "plot_session_analysis.py",
            "analyze_additional_date.py",
            "audit_order_reuse.py",
            "repeatability_analysis.py", "plot_repeatability.py",
        ):
            run([sys.executable, root / "scripts" / script, "--root", root], root, log)
        run([
            sys.executable, root / "scripts/analyze_browser_layout.py",
            "--data", "data/browser-layout-2026-11-22",
            "--out", "results/browser-layout-2026-11-22",
            "--doc", "docs/BROWSER_LAYOUT.md",
        ], root, log)
        run([sys.executable, root / "scripts/plot_browser_layout.py"], root, log)
        if not args.skip_paper:
            run([sys.executable, root / "scripts/build_paper.py", "--root", root], root, log)
        run([sys.executable, root / "scripts/validate_package.py", "--root", root, "--ignore-manifest"], root, log)
        ending = "\nAll offline research checks completed successfully.\n"
        print(ending, end=""); log.write(ending)
    # Close the evidence log before hashing it, avoiding a self-changing manifest.
    subprocess.run([sys.executable, str(root / "scripts/validate_package.py"), "--root", str(root), "--write-manifest"], cwd=root, check=True)
    print("Reproduction complete; SHA256SUMS.txt covers the closed verification log and public artifacts.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError, importlib.metadata.PackageNotFoundError) as error:
        print(f"Reproduction stopped: {error}", file=sys.stderr)
        raise SystemExit(1)
