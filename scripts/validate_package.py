"""Offline checks for research inputs, analysis, public links and SHA-256 coverage."""
from __future__ import annotations

import argparse
import collections
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

IGNORED_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache"}
FIGURES = ("lookup_ecdf", "lookup_paired_distributions", "window_effects", "domain_effects", "page_effects", "setup_breakdown", "timing_series")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def public_files(root):
    files = []
    for folder, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not (Path(folder) == root / "data" and d == "new-run")]
        for name in names:
            p = Path(folder) / name
            rel = p.relative_to(root).as_posix()
            if rel in {"SHA256SUMS.txt", "SON_ADIMLAR_TR.md"} or name.endswith((".pyc", ".pyo")) or name.startswith("npm-debug.log") or name == ".DS_Store":
                continue
            if p.is_symlink():
                raise ValueError(f"Public package contains an unsupported symlink: {rel}")
            files.append(p)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def original_data_checks(root):
    ledger_path = root / "docs/evidence/original-data-sha256.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8-sig"))
    entries = ledger["files"]
    for rel, expected in entries.items():
        target = (root / rel).resolve()
        if not target.is_relative_to(root) or not rel.startswith("data/"):
            raise ValueError("Unsafe protected-data path")
        if not target.is_file() or digest(target) != expected:
            raise ValueError(f"Original November 15 input changed or is absent: {rel}")
    return len(entries)


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def check_dataset(root, data, result):
    raw = rows(data / "dns_raw.jsonl")
    pages = rows(data / "pages.jsonl")
    gates = rows(data / "page-dns.jsonl")
    env = json.loads((data / "environment.json").read_text(encoding="utf-8-sig"))
    if env.get("status") != "complete":
        raise ValueError(f"Collection is incomplete: {data.relative_to(root)}")
    summary = json.loads((result / "summary.json").read_text(encoding="utf-8-sig"))
    measured = [r for r in raw if r.get("phase") == "measure"]
    expected = env["windows"] * env["reps"] * len(env["domains"]) * len(env["providers"]) * 3
    if len(measured) != expected:
        raise ValueError(f"Unexpected measured lookup count in {data.relative_to(root)}")
    design = collections.Counter((r["window"], r["provider"], r["protocol"]) for r in measured)
    if len(design) != env["windows"] * len(env["providers"]) * 3 or set(design.values()) != {env["reps"] * len(env["domains"])}:
        raise ValueError("Lookup groups do not match the recorded design")
    expected_pages = env["windows"] * env["reps"] * len(env["providers"]) * 2 * 3
    if len(pages) != expected_pages:
        raise ValueError("Page attempts do not match the recorded design")
    wanted = {"lookup_all_rows": len(raw), "lookup_measurements": len(measured), "pages": len(pages), "page_dns_rows": len(gates)}
    for name, value in wanted.items():
        if summary["counts"][name] != value:
            raise ValueError(f"Summary count does not match raw inputs: {name}")
    for audit in summary["validation"].values():
        if audit.get("validation_errors") or audit.get("transport_mismatches"):
            raise ValueError(f"Analysis audit failed: {audit['dataset']}")
    if summary.get("warnings"):
        raise ValueError("Analysis reported warnings")
    return {"data": data.relative_to(root).as_posix(), **wanted}


def heading_fragments(source):
    """Return fragments for the ATX headings used in the public Markdown files."""
    fragments = set()
    counters = collections.Counter()
    fenced = False
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        if re.match(r"^\s*(?:`{3,}|~{3,})", line):
            fenced = not fenced
        if fenced:
            continue
        heading = re.match(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if heading:
            title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading[1])
            base = re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-")
            suffix = counters[base]
            fragments.add(f"{base}-{suffix}" if suffix else base)
            counters[base] += 1
    return fragments


def check_links(root):
    checked = 0
    sources = [root / "README.md", root / "manuscript.md", *sorted((root / "docs").rglob("*.md"))]
    for source in sources:
        if not source.exists():
            continue
        for target in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", source.read_text(encoding="utf-8-sig")):
            target = target.strip("<>")
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            local = unquote(url.path)
            destination = (source.parent / local).resolve() if local else source
            if not destination.is_relative_to(root) or not destination.exists():
                raise ValueError(f"Broken local link in {source.relative_to(root)}: {target}")
            if destination.name == "SON_ADIMLAR_TR.md":
                raise ValueError("Public document links to the user's ignored private guide")
            if url.fragment and destination.suffix.lower() == ".md":
                if unquote(url.fragment) not in heading_fragments(destination):
                    raise ValueError(f"Missing Markdown heading in {source.relative_to(root)}: {target}")
            checked += 1
    return checked


def check_figures(root, dates):
    stems = [root / "figures" / stem for stem in FIGURES]
    if len(dates) > 1:
        stems += [root / "figures/replication-2026-11-19" / stem for stem in FIGURES]
        stems.append(root / "figures/cross_date_comparison")
    stems.extend(root / "figures" / stem for stem in (
        "historical_window_sensitivity", "control_window_effects", "control_udp_stages",
        "google_sign_validation", "browser_phases",
        "session_effects", "session_threshold_decisions", "session_pair_magnitudes",
        "session_google_marginals",
        "browser-layout-2026-11-22/layout_delay_effects",
        "repeatability_magnitudes", "repeatability_thresholds", "repeatability_lag_sensitivity",
        "repeatability_fixed_flow_comparison",
    ))
    for stem in stems:
        for extension, signature in ((".png", b"\x89PNG\r\n\x1a\n"), (".pdf", b"%PDF"), (".svg", b"<svg")):
            file = stem.with_suffix(extension)
            data = file.read_bytes()
            if (signature not in data[:1000]) or len(data) < 100:
                raise ValueError(f"Invalid figure artifact: {file.relative_to(root)}")
    return len(stems)


def check_collection_snapshot(root):
    folder = root / "docs/evidence/collection-source-2026-11-19"
    capture = json.loads((folder / "capture.json").read_text(encoding="utf-8-sig"))
    for name, expected in capture["script_sha256"].items():
        file = (folder / name).resolve()
        if not file.is_relative_to(folder) or digest(file) != expected:
            raise ValueError(f"Collection source snapshot hash differs: {name}")
    for line in (folder / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
        expected, name = line.split("  ", 1)
        file = (folder / name).resolve()
        if not file.is_relative_to(folder) or digest(file) != expected:
            raise ValueError(f"Collection snapshot manifest differs: {name}")
    return len(capture["script_sha256"])


def check_followup(root):
    folder = root / "data/control-2026-11-20"
    env = json.loads((folder / "environment.json").read_text(encoding="utf-8-sig"))
    plan = json.loads((folder / "design.json").read_text(encoding="utf-8-sig"))
    if env["status"] != "complete" or any(env[key] != plan[key] for key in (
        "windows", "reps", "providers", "domains", "modes", "seed", "source_sha256"
    )):
        raise ValueError("Follow-up collection is incomplete or differs from its design")
    source = root / "docs/evidence/collection-source-2026-11-20"
    capture = json.loads((source / "capture.json").read_text(encoding="utf-8-sig"))
    if set(plan["source_sha256"]) != {"measure_controls.mjs", "dns_client.mjs"}:
        raise ValueError("Missing follow-up collector source checksums")
    if capture["script_sha256"] != plan["source_sha256"]:
        raise ValueError("Follow-up source ledgers disagree")
    for name, expected in plan["source_sha256"].items():
        if digest(source / name) != expected:
            raise ValueError(f"Follow-up collector differs from the executed source: {name}")
    data_hashes = capture["data_files_sha256"]
    if set(data_hashes) != {"control_raw.jsonl", "design.json", "environment.json", "events.jsonl"}:
        raise ValueError("Missing follow-up data checksums")
    for name, expected in data_hashes.items():
        if digest(folder / name) != expected:
            raise ValueError(f"Follow-up input differs from the collected file: {name}")
    raw = rows(folder / "control_raw.jsonl")
    measured = [r for r in raw if r["phase"] == "measure"]
    primed = [r for r in raw if r["phase"] == "prime"]
    expected = env["windows"] * len(env["providers"]) * len(env["domains"]) * len(env["modes"])
    if (len(measured) != expected * env["reps"] or len(primed) != expected
            or len(raw) != len(measured) + len(primed)
            or env["total_rows"] != len(raw) or env["measured_rows"] != len(measured)
            or env["valid_rows"] != sum(r["valid"] is True for r in raw)
            or capture["measured_attempts"] != len(measured) or capture["priming_attempts"] != len(primed)):
        raise ValueError("Follow-up attempt totals disagree with the plan or collection metadata")
    return {
        "windows": env["windows"], "measured": len(measured), "priming": len(primed),
        "measured_failures": sum(r["valid"] is not True for r in measured),
    }


def check_data_ledger(root, ledger, required=None, relative_base=None):
    listed = set()
    base = root if relative_base is None else (root / relative_base).resolve()
    for line in (root / ledger).read_text(encoding="utf-8-sig").splitlines():
        expected, relative = line.split("  ", 1)
        target = (base / relative).resolve()
        if relative in listed or not target.is_relative_to(base) or digest(target) != expected:
            raise ValueError(f"Saved artifact checksum mismatch or unsafe path: {relative}")
        listed.add(relative)
    if not listed or (required and not required <= listed):
        raise ValueError(f"Incomplete artifact ledger: {ledger}")
    return len(listed)


def check_session_extension(root):
    plan_path = root / "docs/SESSION_EXTENSION_PLAN.json"
    source = root / "docs/evidence/collection-source-2026-11-22"
    capture = json.loads((source / "capture.json").read_text(encoding="utf-8"))
    if digest(plan_path) != capture["plan_sha256"] or not capture["strict_serial_order"]:
        raise ValueError("Held-out collection does not match its frozen plan or chronology")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if any(capture["script_sha256"].get(name) != value
           for name, value in plan["maintained_source_sha256"].items()):
        raise ValueError("Executed session source does not match the plan")
    for name, expected in capture["script_sha256"].items():
        target = (source / name).resolve()
        if not target.is_relative_to(source) or digest(target) != expected:
            raise ValueError(f"Held-out source checksum mismatch: {name}")
    summary = json.loads((root / "results/session_extension/summary.json").read_text(encoding="utf-8"))
    by_id = {row["session_id"]: row for row in summary["sessions"]}
    if (set(by_id) != {row["session_id"] for row in plan["sessions"]}
            or not summary["chronology"]["is_final"]):
        raise ValueError("Session extension summary does not cover the frozen plan")
    measured = 0
    expected_files = set()
    session_spans = []
    for item in plan["sessions"]:
        result = by_id[item["session_id"]]
        folder = root / item["directory"]
        env = json.loads((folder / "environment.json").read_text(encoding="utf-8"))
        if (result["status"] != "complete" or env["status"] != "complete"
                or env["measured_rows"] != item["expected_measured_attempts"]):
            raise ValueError(f"Session extension collection is incomplete: {item['session_id']}")
        measured += env["measured_rows"]
        session_spans.append((datetime.fromisoformat(env["started_utc"]), datetime.fromisoformat(env["finished_utc"])))
        expected_files.update(f"{item['directory']}/{name}" for name in (
            "control_raw.jsonl", "environment.json", "design.json", "events.jsonl",
        ))
    hashes = capture["data_files_sha256"]
    if not expected_files <= set(hashes):
        raise ValueError("Missing held-out data checksums")
    for relative, expected in hashes.items():
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or digest(target) != expected:
            raise ValueError(f"Held-out data checksum mismatch: {relative}")
    loopback_dir = "data/loopback-2026-11-22/"
    loopback_files = check_data_ledger(
        root, loopback_dir + "SHA256SUMS.txt",
        {loopback_dir + "loopback_raw.jsonl", loopback_dir + "loopback_environment.json"},
    )
    loopback = json.loads((root / "results/loopback_summary.json").read_text(encoding="utf-8"))
    loopback_env = json.loads((root / loopback_dir / "loopback_environment.json").read_text(encoding="utf-8"))
    browser_dir = "data/browser-layout-2026-11-22"
    browser_files = check_data_ledger(
        root, browser_dir + "/SHA256SUMS.txt",
        {"pages.jsonl", "design.json", "environment.json", "completion.json", "schedule.json",
         "fixture.html", "fixture.svg", "analyzer_snapshot.py", "collector_snapshot.mjs"},
        relative_base=browser_dir,
    )
    browser = json.loads((root / "results/browser-layout-2026-11-22/summary.json").read_text(encoding="utf-8"))
    if loopback["complete_pairs"] < 1 or browser["counts"]["invalid"] or browser["completion"]["status"] != "complete":
        raise ValueError("Loopback or browser layout results failed validation")
    other_spans = [
        (loopback_env["started_utc"], loopback_env["finished_utc"]),
        (browser["environment"]["started_utc"], browser["completion"]["finished_utc"]),
    ]
    for started, finished in other_spans:
        start, end = datetime.fromisoformat(started), datetime.fromisoformat(finished)
        if end < start or any(start < peer_end and peer_start < end for peer_start, peer_end in session_spans):
            raise ValueError("A local calibration overlaps a held-out public DNS session")
    verification_dir = "data/verification-2026-11-23"
    check_data_ledger(
        root, verification_dir + "/SHA256SUMS.txt",
        {"docs/ADDITIONAL_DATE_PLAN.json", *(verification_dir + "/" + name for name in (
            "design.json", "environment.json", "events.jsonl", "control_raw.jsonl",
        ))},
    )
    verification = json.loads((root / "results/additional_date.json").read_text(encoding="utf-8"))
    if verification["audit"]["errors"] or datetime.fromisoformat(verification["started_utc"]) <= session_spans[-1][1]:
        raise ValueError("Additional-date held-out audit or chronology failed")
    return {
        "completed_sessions": len(by_id), "measured_attempts": measured,
        "loopback_files": loopback_files, "loopback_pairs": loopback["complete_pairs"],
        "browser_delay_injection_attempts": browser["counts"]["attempted"], "browser_raw_files": browser_files,
        "additional_date_attempts": verification["audit"]["measured_attempts"],
    }


def check_repeatability(root):
    plan_file = root / "docs/REPEATABILITY_PLAN.json"
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    lock = json.loads((root / plan["source_lock"]).read_text(encoding="utf-8"))
    summary = json.loads((root / "results/repeatability/summary.json").read_text(encoding="utf-8"))
    if lock["plan_sha256"] != digest(plan_file) or lock["source_sha256"] != plan["source_sha256"]:
        raise ValueError("Repeatability source lock differs from the frozen plan")
    archive = root / "docs/evidence/repeatability-source-2026-11-23"
    for name, expected in plan["source_sha256"].items():
        target = (archive / name).resolve()
        if not target.is_relative_to(archive) or digest(target) != expected:
            raise ValueError(f"Repeatability source differs from the frozen copy: {name}")
    statuses = {run["run_id"]: run for run in summary["runs"]}
    completed, measured, failed, schedules = [], 0, 0, set()
    for planned in plan["runs"]:
        run = statuses[planned["run_id"]]
        folder = root / planned["directory"]
        if planned["optional"] and not folder.exists() and run["status"] == "not_collected":
            continue
        if run["status"] != "complete" or run["audit"]["errors"]:
            raise ValueError(f"Repeatability run is incomplete or invalid: {run['run_id']}")
        env = json.loads((folder / "environment.json").read_text(encoding="utf-8"))
        audit = run["audit"]
        raw = folder / "repeatability_raw.jsonl"
        captured = json.loads((archive / f"{run['run_id']}-capture.json").read_text(encoding="utf-8"))
        captured_hashes = captured["data_files_sha256"]
        if (captured["plan_sha256"] != lock["plan_sha256"] or captured["script_sha256"] != plan["source_sha256"]
                or captured_hashes.get(raw.relative_to(root).as_posix()) != audit["raw_sha256"]):
            raise ValueError(f"Repeatability capture ledger does not match the plan or analysis: {run['run_id']}")
        for relative, expected in captured_hashes.items():
            target = (root / relative).resolve()
            if not target.is_relative_to(folder) or digest(target) != expected:
                raise ValueError(f"Repeatability capture checksum mismatch: {relative}")
        if (env["source_sha256"] != plan["source_sha256"] or not audit["plan_and_lock_precede_start"]
                or digest(raw) != audit["raw_sha256"] or env["status"] != "complete"
                or env["measured_rows"] != plan["design"]["expected_measured_attempts_per_run"]
                or audit["measured_attempts"] != env["measured_rows"]
                or len(audit["schedule_hashes"]) != plan["design"]["windows"]):
            raise ValueError(f"Repeatability evidence differs from its collection: {run['run_id']}")
        completed.append(run["run_id"])
        measured += audit["measured_attempts"]
        failed += audit["failed_measured_attempts"]
        schedules.update(audit["schedule_hashes"].values())
    if completed != summary["completed_run_ids"] or len(schedules) != len(completed) * plan["design"]["windows"]:
        raise ValueError("Repeatability runs or unique schedules disagree with the audit")
    return {"completed_runs": completed, "measured_attempts": measured,
            "failed_measured_attempts": failed, "distinct_schedules": len(schedules)}


def manifest(root, write=False):
    file = root / "SHA256SUMS.txt"
    public = public_files(root)
    if write:
        file.write_text("".join(f"{digest(p)}  {p.relative_to(root).as_posix()}\n" for p in public), encoding="utf-8")
    listed = {}
    for line in file.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match or match[2] in listed:
            raise ValueError("Malformed or duplicate SHA256SUMS entry")
        listed[match[2]] = match[1]
    expected_names = {p.relative_to(root).as_posix() for p in public}
    if set(listed) != expected_names:
        raise ValueError(f"Manifest coverage differs: missing={sorted(expected_names-set(listed))}; extra={sorted(set(listed)-expected_names)}")
    for rel, expected in listed.items():
        target = (root / rel).resolve()
        if not target.is_relative_to(root) or digest(target) != expected:
            raise ValueError(f"SHA-256 mismatch: {rel}")
    return len(listed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--raw-only", action="store_true", help="Verify the frozen original inputs before a rebuild")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ignore-manifest", action="store_true")
    group.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    protected = original_data_checks(root)
    if args.raw_only:
        print(json.dumps({"status": "PASS", "protected_original_inputs": protected}, indent=2))
        return
    required = ["README.md", "package.json", "package-lock.json", "requirements.txt", "profile.json", "manuscript.md", "docs/paper_source.md", "docs/references.json", "scripts/analyze.py", "scripts/build_paper.py", "scripts/plot_results.py", "scripts/robustness.py", "scripts/reproduce.py", "scripts/dns_client.mjs", "scripts/measure_dns.mjs", "scripts/page-load.mjs", "tests/test_analysis.py", "tests/test_dns.mjs", "tests/test_live.mjs"]
    for rel in required:
        if not (root / rel).is_file():
            raise ValueError(f"Required public file absent: {rel}")
    package = json.loads((root / "package.json").read_text(encoding="utf-8-sig"))
    lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8-sig"))
    if package["dependencies"] != lock["packages"][""]["dependencies"] or package["version"] != lock["version"]:
        raise ValueError("package.json and package-lock.json disagree")
    profile = json.loads((root / "profile.json").read_text(encoding="utf-8-sig"))
    if any(not str(profile.get(k, "")).strip() for k in ("author_name", "student_id", "institution", "repository_url")):
        raise ValueError("Author profile incomplete")
    json.loads((root / "docs/references.json").read_text(encoding="utf-8-sig"))
    pdf = root / "Secure_DNS_Research_Paper.pdf"
    if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF"):
        raise ValueError("Final paper PDF absent or invalid")
    datasets = [check_dataset(root, root / "data", root / "results")]
    replica = root / "data/replication-2026-11-19"
    snapshot_files = 0
    if replica.exists():
        datasets.append(check_dataset(root, replica, root / "results/replication-2026-11-19"))
        snapshot_files = check_collection_snapshot(root)
    followup = check_followup(root)
    extension = check_session_extension(root)
    repeatability = check_repeatability(root)
    figure_count = check_figures(root, datasets)
    for name in ("control_analysis.json", "browser_phases.csv"):
        if not (root / "results" / name).is_file():
            raise ValueError(f"Missing revised analysis: {name}")
    links = check_links(root)
    coverage = None if args.ignore_manifest else manifest(root, args.write_manifest)
    print(json.dumps({"status": "PASS", "protected_original_inputs": protected, "collection_snapshot_files": snapshot_files, "datasets": datasets, "followup": followup, "session_extension": extension, "repeatability": repeatability, "figure_stems": figure_count, "local_links_checked": links, "manifest_files": coverage, "network_access": "none"}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
