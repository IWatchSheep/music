"""Run unittest tests and write one JSON record per test (child process of run_acceptance.py).

Usage: python acceptance/unittest_json.py <project_root> <output.json> <discover|module> [module ...]

The process exit code is 0 only when the run was successful (no failures or errors).
Standard library only.
"""

from __future__ import annotations

import json
import os
import sys
import time
import unittest


class _RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = {}
        self._t0 = {}

    def startTest(self, test):
        self._t0[test.id()] = time.perf_counter()
        super().startTest(test)

    def _rec(self, test, status, detail=""):
        tid = test.id()
        self.records[tid] = {"status": status, "seconds": round(time.perf_counter() - self._t0.get(tid, time.perf_counter()), 3),
                             "detail": detail[-4000:]}

    def addSuccess(self, test):
        super().addSuccess(test); self._rec(test, "pass")

    def addFailure(self, test, err):
        super().addFailure(test, err); self._rec(test, "fail", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        if isinstance(test, unittest.TestCase):
            self._rec(test, "error", self._exc_info_to_string(err, test))
        else:                                  # module/class-level error (e.g. import failure)
            self.records[str(test)] = {"status": "error", "seconds": 0.0, "detail": self._exc_info_to_string(err, test)[-4000:]}

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self._rec(test, "skip", reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err); self._rec(test, "expected_failure")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self._rec(test, "unexpected_success")


def _ids(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from _ids(t)
        else:
            yield t.id()


def main(argv) -> int:
    root, out, mode, *modules = argv
    os.chdir(root)
    sys.path.insert(0, root)
    loader = unittest.TestLoader()
    if mode == "discover":
        suite = loader.discover("tests", top_level_dir=".")
    else:
        suite = loader.loadTestsFromNames([mode] + modules)
    collected = sorted(_ids(suite))
    runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=1, resultclass=_RecordingResult)
    t0 = time.perf_counter()
    result = runner.run(suite)
    payload = {
        "python": sys.version, "executable": sys.executable, "platform": sys.platform,
        "collected": collected, "results": result.records, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "successful": result.wasSuccessful(), "seconds": round(time.perf_counter() - t0, 3),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
