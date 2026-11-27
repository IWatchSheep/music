"""JOB-03 / JOB-04 independent acceptance runner (standard library only).

Run from anywhere; paths are resolved relative to this file's project root:

    python acceptance/run_acceptance.py                      # platform-independent acceptance
    python acceptance/run_acceptance.py --windows-device     # + opt-in real Windows MCI device tests
    xvfb-run -a python acceptance/run_acceptance.py          # Linux without a display (Tk needs one)

Each step runs in its own child process, and its OWN exit code is recorded (no pipeline consumers).
Results are written to <project>/acceptance_results/<UTC timestamp>/ (report.md, report.json, logs).
Exit code: 0 when no requirement FAILs or is INCOMPLETE, the full suite succeeds, all nine REQUIRED
standalone scripts are present and exit 0 (plus the OPTIONAL experimental script when present), and
the matrix references only existing tests; 1 otherwise; 2 on a runner error.  The required scripts
include the JOB-04 group-discovery verification and ChatGPT's independent held-out verifier.  The one
optional script (row merger) is outside the publication boundary: it runs only if present.
Every script runs with the project root prepended to PYTHONPATH (the held-out verifier needs it).

Status vocabulary (per requirement):
  PASS         every mapped platform-independent test passed and every mapped script exited 0
  FAIL         a mapped test failed/errored/is missing, or a mapped script exited non-zero
  INCOMPLETE   a mapped platform-independent test was skipped in this environment
  NO-AUTOMATED-COVERAGE  physical or unresolved item; see 'remaining_unverified'
Windows device evidence is reported in its own column: PASS/FAIL/SKIP when run here, otherwise
'NOT RUN HERE' with the recorded Windows evidence.  Simulated timing is never an acoustic measurement.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEVICE_MODULE = "tests.test_playback_windows_device"
# Required: always executed; a missing or failing required script fails acceptance.
# The last two are JOB-04: the group-discovery verification and the independent held-out verifier
# (supplied by ChatGPT; kept byte-identical; exits non-zero if any of its checks fails).
REQUIRED_SCRIPTS = ["verify_audio_and_sheet_adapters.py", "verify_development.py", "verify_group_units.py",
                    "verify_midi_import.py", "verify_playback_transport.py", "verify_progressive.py",
                    "verify_proof.py", "verify_group_discovery.py", "job04_investigation/job04_heldout_audit.py"]
# Unpublished experiment outside the publication boundary (row merger).  Executed only when present
# (a present script that fails still fails acceptance); when absent it is reported as
# OUTSIDE PUBLICATION SCOPE and does not affect the result.
OPTIONAL_SCRIPTS = ["verify_row_merger.py"]
OUTSIDE_SCOPE = "OUTSIDE PUBLICATION SCOPE (absent)"


def _run(cmd, log_path, env=None, timeout=3600):
    t0 = time.perf_counter()
    with open(log_path, "w", encoding="utf-8", errors="replace") as log:
        try:
            rc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
    return rc, round(time.perf_counter() - t0, 1)


def _tests_step(label, out_dir, spec, env):
    js = os.path.join(out_dir, f"{label}.json")
    cmd = [sys.executable, "-X", "faulthandler", os.path.join(HERE, "unittest_json.py"), ROOT, js] + spec
    rc, secs = _run(cmd, os.path.join(out_dir, f"{label}.log"), env=env)
    data = None
    if os.path.exists(js):
        with open(js, encoding="utf-8") as f:
            data = json.load(f)
    print(f"[{label}] python exit code = {rc} ({secs} s)"
          + (f"; run={data['tests_run']} failures={data['failures']} errors={data['errors']} skipped={data['skipped']}" if data else "; NO RESULT FILE"),
          flush=True)
    return {"exit_code": rc, "seconds": secs, "data": data}


def _status_of(tid, *result_sets):
    for rs in result_sets:
        if rs and rs.get("data") and tid in rs["data"]["results"]:
            return rs["data"]["results"][tid]["status"]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--windows-device", action="store_true", help="also run the opt-in real Windows MCI device tests")
    ap.add_argument("--skip-scripts", action="store_true", help="do not run the standalone scripts (reported as NOT RUN)")
    args = ap.parse_args()

    with open(os.path.join(HERE, "acceptance_matrix.json"), encoding="utf-8") as f:
        matrix = json.load(f)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.join(ROOT, "acceptance_results", stamp)
    os.makedirs(out_dir, exist_ok=True)
    print(f"JOB-03/JOB-04 acceptance runner | python {platform.python_version()} | {sys.platform} | results: {out_dir}", flush=True)

    # 1. Complete platform-independent suite.  The opt-in flag is removed so device tests stay separate.
    env = dict(os.environ); env.pop("MUSIC_REAL_AUDIO_TESTS", None)
    suite = _tests_step("suite", out_dir, ["discover"], env)

    # 2. Opt-in real Windows device tests (separately identifiable).
    device = None
    if args.windows_device:
        if os.name != "nt":
            print("[device] --windows-device ignored: not Windows", flush=True)
        else:
            denv = dict(os.environ); denv["MUSIC_REAL_AUDIO_TESTS"] = "1"
            device = _tests_step("device", out_dir, [DEVICE_MODULE], denv)

    # 3. Standalone verification scripts (project root prepended to PYTHONPATH).
    senv = dict(os.environ)
    senv["PYTHONPATH"] = ROOT + (os.pathsep + senv["PYTHONPATH"] if senv.get("PYTHONPATH") else "")
    scripts = {}
    for s in REQUIRED_SCRIPTS + OPTIONAL_SCRIPTS:
        required = s in REQUIRED_SCRIPTS
        if args.skip_scripts:
            scripts[s] = {"exit_code": "NOT RUN", "seconds": 0, "required": required}
            continue
        if not os.path.isfile(os.path.join(ROOT, s)):
            scripts[s] = {"exit_code": "MISSING" if required else OUTSIDE_SCOPE, "seconds": 0, "required": required}
            print(f"[script] {s}: {'MISSING (required)' if required else OUTSIDE_SCOPE}", flush=True)
            continue
        rc, secs = _run([sys.executable, "-X", "faulthandler", s],
                        os.path.join(out_dir, "script_" + s.replace("/", "_") + ".log"), env=senv)
        scripts[s] = {"exit_code": rc, "seconds": secs, "required": required}
        print(f"[script] {s} ({'required' if required else 'optional, present'}): python exit code = {rc} ({secs} s)", flush=True)

    collected = set(suite["data"]["collected"]) if suite["data"] else set()
    if device and device["data"]:
        collected |= set(device["data"]["collected"])
    device_ids = {t for t in collected if t.startswith(DEVICE_MODULE + ".")}

    # 4. Per-requirement evaluation.
    rows, matrix_errors = [], []
    for req in matrix["requirements"]:
        auto = []
        for tid in req["automated_tests"]:
            if tid == "ALL":
                ok = bool(suite["data"]) and suite["data"]["successful"] and suite["exit_code"] == 0
                auto.append({"test": "ALL (complete suite)", "status": "pass" if ok else "fail"})
                continue
            st = _status_of(tid, suite)
            if st is None:
                matrix_errors.append(f"{req['id']}: unknown test id {tid}")
                st = "missing"
            auto.append({"test": tid, "status": st})
        scr = [{"script": s, "exit_code": scripts.get(s, {}).get("exit_code", "NOT RUN"), "optional": False} for s in req["scripts"]]
        scr += [{"script": s, "exit_code": scripts.get(s, {}).get("exit_code", "NOT RUN"), "optional": True}
                for s in req.get("optional_scripts", [])]
        dev = []
        dev_ids = sorted(device_ids) if req["windows_device_tests"] == ["ALL_DEVICE"] else req["windows_device_tests"]
        for tid in dev_ids:
            if tid not in collected:
                matrix_errors.append(f"{req['id']}: unknown device test id {tid}")
                dev.append({"test": tid, "status": "missing"}); continue
            st = _status_of(tid, device, suite) if tid.startswith(DEVICE_MODULE + ".") and device else _status_of(tid, suite)
            if tid.startswith(DEVICE_MODULE + ".") and device is None:
                st = "not run here"
            dev.append({"test": tid, "status": st})

        auto_st = [a["status"] for a in auto]
        if any(s in ("fail", "error", "missing", "unexpected_success") for s in auto_st) or \
           any(c["exit_code"] not in (0, "NOT RUN", OUTSIDE_SCOPE) for c in scr) or any(d["status"] in ("fail", "error", "missing") for d in dev):
            status = "FAIL"
        elif any(s == "skip" for s in auto_st) or any(c["exit_code"] == "NOT RUN" and not c["optional"] for c in scr):
            status = "INCOMPLETE"
        elif not auto and not scr:
            status = "NO-AUTOMATED-COVERAGE"
        else:
            status = "PASS"
        if req.get("kind") in ("physical", "unresolved") and status == "PASS":
            status = "PASS (regression only; see remaining_unverified)"
        if req.get("kind") in ("physical", "unresolved") and status == "INCOMPLETE" and not auto:
            status = "NO-AUTOMATED-COVERAGE"
        if dev and all(d["status"] == "not run here" for d in dev if d["test"].startswith(DEVICE_MODULE)):
            dev_summary = "NOT RUN HERE (recorded: " + "; ".join(req["recorded_windows_evidence"] or ["none"]) + ")"
        elif dev:
            ds = [d["status"] for d in dev]
            dev_summary = ("FAIL" if any(s in ("fail", "error", "missing") for s in ds) else
                           "PASS" if all(s == "pass" for s in ds) else
                           "PARTIAL (" + ", ".join(f"{d['test'].rsplit('.', 1)[-1]}={d['status']}" for d in dev if d["status"] != "pass") + ")")
        else:
            dev_summary = "n/a"
        rows.append({"id": req["id"], "title": req["title"], "status": status, "automated": auto, "scripts": scr,
                     "windows_device": dev, "windows_device_summary": dev_summary,
                     "recorded_windows_evidence": req["recorded_windows_evidence"],
                     "author_observation": req["author_observation"], "remaining_unverified": req["remaining_unverified"]})

    skipped = {}
    if suite["data"]:
        for tid, r in suite["data"]["results"].items():
            if r["status"] == "skip":
                skipped[tid] = r["detail"]
    unexpected_skips = {t: why for t, why in skipped.items()
                        if not t.startswith(DEVICE_MODULE + ".") and "No Windows MCI device" not in why}

    gate_ok = (suite["exit_code"] == 0 and bool(suite["data"]) and suite["data"]["successful"]
               and all(v["exit_code"] == 0 for v in scripts.values() if v["exit_code"] not in ("NOT RUN", OUTSIDE_SCOPE))
               and not matrix_errors and not unexpected_skips
               and all(r["status"] not in ("FAIL", "INCOMPLETE") for r in rows)
               and (device is None or (device["exit_code"] == 0 and device["data"] and device["data"]["successful"])))

    sd = suite["data"] or {}
    report = {
        "generated_utc": stamp, "python": sys.version, "platform": platform.platform(), "executable": sys.executable,
        "suite": {"exit_code": suite["exit_code"], "run": sd.get("tests_run"), "failures": sd.get("failures"),
                  "errors": sd.get("errors"), "skipped": sd.get("skipped"),
                  "passed": (sd.get("tests_run", 0) - sd.get("failures", 0) - sd.get("errors", 0) - sd.get("skipped", 0)) if sd else None,
                  "seconds": suite["seconds"]},
        "device": None if device is None else {"exit_code": device["exit_code"], "run": device["data"]["tests_run"] if device["data"] else None,
                                               "failures": device["data"]["failures"] if device["data"] else None,
                                               "errors": device["data"]["errors"] if device["data"] else None,
                                               "skipped": device["data"]["skipped"] if device["data"] else None},
        "scripts": scripts, "skipped_tests": skipped, "unexpected_skips": unexpected_skips,
        "matrix_errors": matrix_errors, "requirements": rows,
        "optional_physical_observations": matrix.get("optional_physical_observations", []),
        "overall": "ACCEPTANCE CHECKS PASSED" if gate_ok else "ACCEPTANCE CHECKS FAILED",
        "disclaimer": "Simulated and device timing figures are software/driver measurements, not acoustic measurements.",
    }
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    _write_markdown(report, os.path.join(out_dir, "report.md"))

    s = report["suite"]
    print(f"\nSUITE: run={s['run']} passed={s['passed']} skipped={s['skipped']} failures={s['failures']} errors={s['errors']} (exit {s['exit_code']})")
    if device is not None:
        print(f"DEVICE: {report['device']}")
    for r in rows:
        print(f"  {r['id']:<4} {r['status']:<48} device: {r['windows_device_summary'][:60]}")
    if matrix_errors:
        print("MATRIX ERRORS:", *matrix_errors, sep="\n  ")
    if unexpected_skips:
        print("UNEXPECTED SKIPS:", *unexpected_skips, sep="\n  ")
    print(f"\n{report['overall']}  -> {os.path.join(out_dir, 'report.md')}")
    return 0 if gate_ok else 1


def _write_markdown(rep, path):
    s = rep["suite"]
    L = [f"# JOB-03 / JOB-04 Acceptance Report ({rep['generated_utc']})", "",
         f"- Python: `{rep['python'].split()[0]}` on `{rep['platform']}`",
         f"- **Overall: {rep['overall']}**",
         f"- Complete suite: run {s['run']}, **passed {s['passed']}, skipped {s['skipped']}**, failures {s['failures']}, errors {s['errors']} (python exit code {s['exit_code']})"]
    if rep["device"]:
        d = rep["device"]
        L.append(f"- Real Windows device tests: run {d['run']}, failures {d['failures']}, errors {d['errors']}, skipped {d['skipped']} (python exit code {d['exit_code']})")
    else:
        L.append("- Real Windows device tests: **not run here** (opt-in, Windows only: `--windows-device`)")
    L.append("- Standalone scripts: " + ", ".join(f"{k} = {v['exit_code']}" for k, v in rep["scripts"].items()))
    L += ["", f"> {rep['disclaimer']}", "", "## Requirements", "",
          "| ID | Requirement | Automated (this run) | Windows device | Author observation | Remaining unverified |",
          "|---|---|---|---|---|---|"]
    for r in rep["requirements"]:
        n = len(r["automated"]); np_ = sum(a["status"] == "pass" for a in r["automated"])
        req_scr = [c for c in r["scripts"] if not c["optional"]]
        opt_txt = ", ".join("%s=%s" % (c["script"], c["exit_code"]) for c in r["scripts"] if c["optional"])
        auto = (f"**{r['status']}** ({np_}/{n} tests"
                + (f"; required scripts {sum(c['exit_code'] == 0 for c in req_scr)}/{len(req_scr)}" if req_scr else "")
                + (f"; optional scripts: {opt_txt}" if opt_txt else "") + ")")
        L.append(f"| {r['id']} | {r['title']} | {auto} | {r['windows_device_summary']} | {r['author_observation'] or '—'} | "
                 f"{'; '.join(r['remaining_unverified']) or '—'} |")
    L += ["", "## Test mapping", ""]
    for r in rep["requirements"]:
        L.append(f"### {r['id']} — {r['status']}")
        for a in r["automated"]:
            L.append(f"- [{a['status']}] `{a['test']}`")
        for c in r["scripts"]:
            L.append(f"- [{'optional; ' if c['optional'] else ''}exit {c['exit_code']}] script `{c['script']}`")
        for d in r["windows_device"]:
            L.append(f"- [device: {d['status']}] `{d['test']}`")
        L.append("")
    L += ["## Skipped tests in the complete suite", ""]
    L += [f"- `{t}`: {why}" for t, why in sorted(rep["skipped_tests"].items())] or ["- none"]
    if rep["unexpected_skips"]:
        L += ["", "**Unexpected skips (gate failure):**"] + [f"- `{t}`" for t in rep["unexpected_skips"]]
    if rep["matrix_errors"]:
        L += ["", "**Matrix errors (gate failure):**"] + [f"- {e}" for e in rep["matrix_errors"]]
    L += ["", "## Optional physical observations (need speakers; not required for automated acceptance)", ""]
    L += [f"- {p['id']}: {p['text']}" for p in rep["optional_physical_observations"]]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as ex:                      # runner defect, distinct from a test failure
        import traceback
        traceback.print_exc()
        print(f"RUNNER ERROR: {ex}", file=sys.stderr)
        sys.exit(2)
