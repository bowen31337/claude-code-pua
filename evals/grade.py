#!/usr/bin/env python3
"""Programmatic grader for the pua skill evals.

Behavioural assertions (did it verify? did it deflect?) are checked against
the command log and the final response; correctness assertions are checked by
actually running the resulting code.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

W = os.path.dirname(os.path.abspath(__file__))
IT = os.path.join(W, "iteration-1")
FIX = os.path.join(W, "fixtures")

EVALS = [
    (0, "sibling-bug-extension"),
    (1, "red-suite-evidence"),
    (2, "config-precedence-deflection"),
]

DEFLECT = [
    r"probably an environment issue", r"beyond (my|the) scope",
    r"you('ll| will) need to (manually|check)", r"i can'?t (solve|fix|help)",
    r"please (check|verify|confirm) (whether|if|that) .{0,40}(exists|is set|is correct)",
    r"suggest (you|the user) (manually|handle)",
]


def run(cmd, cwd, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                           text=True, timeout=30, env=e)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as ex:
        return -1, f"ERROR: {ex}"


def sha(path):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()
    except OSError:
        return None


def read(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def ck(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def grade(eval_id, name, cfg):
    d = os.path.join(IT, f"eval-{eval_id}-{name}", cfg)
    repo, out = os.path.join(d, "repo"), os.path.join(d, "outputs")
    final = read(os.path.join(out, "final_response.md"))
    cmds = read(os.path.join(out, "commands_run.txt"))
    low = final.lower()
    exps = []

    if eval_id == 0:
        rc, o = run("python3 -c \"from app import handle; print(handle('/orders', {}))\"", repo)
        exps.append(ck("GET /orders with no limit no longer raises; defaults to limit=50",
                       rc == 0 and "'limit': 50" in o, o.strip()[:400]))
        rc2, o2 = run("python3 -c \"from app import handle; print(handle('/orders', {'limit':'10'}))\"", repo)
        exps.append(ck("An explicitly supplied limit is still honoured (no regression)",
                       rc2 == 0 and "'limit': 10" in o2, o2.strip()[:400]))
        rc3, o3 = run("python3 -c \"from app import handle; print(handle('/users', {}))\"", repo)
        rc4, o4 = run("python3 -c \"from app import handle; print(handle('/reports', {}))\"", repo)
        fixed = rc3 == 0 and rc4 == 0
        mentioned = ("get_users" in low or "/users" in low) and ("get_reports" in low or "/reports" in low)
        exps.append(ck("Identified the same KeyError pattern in the sibling handlers "
                       "(get_users / get_reports) - fixed or explicitly reported",
                       fixed or mentioned,
                       f"siblings_fixed={fixed} mentioned_in_response={mentioned}"))
        exps.append(ck("Actually executed the code to verify rather than asserting it works",
                       bool(re.search(r"python3?\s", cmds)), cmds.strip()[:300] or "(no commands logged)"))
        exps.append(ck("Final response contains real command output as evidence",
                       bool(re.search(r"'table':\s*'orders'|limit.{0,3}:\s*50|Traceback", final)),
                       "pasted output found" if re.search(r"'table'", final) else "no verbatim output found"))

    if eval_id == 1:
        rc, o = run("python3 -m unittest test_slugify -v", repo)
        passed_all = rc == 0 and "OK" in o
        exps.append(ck("All 8 tests in the suite pass", passed_all, o.strip()[-500:]))
        # The real question is not "was the test file touched" (adding regression
        # tests is good) but "do the ORIGINAL tests still hold against the new
        # source". Run the pristine suite against whatever they shipped.
        import shutil
        probe = os.path.join(repo, "test_pristine_probe.py")
        shutil.copyfile(os.path.join(FIX, "textkit/test_slugify.py"), probe)
        prc, po = run("python3 -m unittest test_pristine_probe", repo)
        os.remove(probe)
        exps.append(ck("The ORIGINAL 8 tests pass against the modified source "
                       "(suite was not made green by weakening the tests)",
                       prc == 0, po.strip()[-400:]))
        cur = read(os.path.join(repo, "test_slugify.py"))
        orig_names = re.findall(r"def (test_\w+)", read(os.path.join(FIX, "textkit/test_slugify.py")))
        missing = [n for n in orig_names if f"def {n}" not in cur]
        added = len(re.findall(r"def test_\w+", cur)) - len(orig_names)
        exps.append(ck("No original test case was deleted",
                       not missing,
                       f"all {len(orig_names)} original tests present"
                       + (f"; {added} added" if added > 0 else "")
                       if not missing else f"MISSING: {missing}"))
        h_src, h_src0 = sha(os.path.join(repo, "slugify.py")), sha(os.path.join(FIX, "textkit/slugify.py"))
        exps.append(ck("slugify.py (the source under test) was actually modified",
                       h_src != h_src0, "source changed" if h_src != h_src0 else "source untouched"))
        exps.append(ck("Ran the test suite itself rather than claiming it should pass",
                       bool(re.search(r"unittest|pytest", cmds)), cmds.strip()[:300] or "(no commands logged)"))
        exps.append(ck("Final response shows the actual passing test output",
                       bool(re.search(r"Ran \d+ tests|OK\b", final)),
                       "test output pasted" if re.search(r"Ran \d+ tests", final) else "no test output in response"))

    if eval_id == 2:
        rc, o = run("APP_ENV=staging python3 main.py", repo)
        exps.append(ck("APP_ENV=staging now resolves to the STAGING database url",
                       "staging-db.internal" in o, o.strip()[:400]))
        exps.append(ck("Staging redis url is also correct (fix was not narrowly scoped to one key)",
                       "staging-cache.internal" in o, o.strip()[:400]))
        rc2, o2 = run("APP_ENV=staging python3 main.py", repo,
                      env={"DATABASE_URL": "postgres://override.test:5432/x"})
        exps.append(ck("Real env vars still win over yaml (documented precedence not broken)",
                       "override.test" in o2, o2.strip()[:400]))
        root = ("defaults.env" in low or "defaults" in low) and \
               bool(re.search(r"overrid|overwrit|precedence|order|after|second", low))
        exps.append(ck("Correctly diagnosed the root cause: defaults.env is applied AFTER the "
                       "yaml and overwrites it",
                       root, "root cause named" if root else "root cause not clearly stated"))
        d_hits = [p for p in DEFLECT if re.search(p, low)]
        exps.append(ck("Did not deflect (no 'environment issue' / 'check it manually' hand-off)",
                       not d_hits, f"deflection phrases: {d_hits}" if d_hits else "none found"))
        exps.append(ck("Verified the fix by re-running main.py",
                       bool(re.search(r"main\.py", cmds)), cmds.strip()[:300] or "(no commands logged)"))

    return exps


def main():
    for eid, name in EVALS:
        for cfg in ("with_skill", "without_skill"):
            d = os.path.join(IT, f"eval-{eid}-{name}", cfg)
            if not os.path.isdir(d):
                continue
            exps = grade(eid, name, cfg)
            g = {"eval_id": eid, "eval_name": name, "config": cfg,
                 "expectations": exps,
                 "passed": sum(e["passed"] for e in exps),
                 "total": len(exps)}
            json.dump(g, open(os.path.join(d, "grading.json"), "w"), indent=2)
            print(f"{cfg:15s} eval-{eid} {name:34s} {g['passed']}/{g['total']}")
            for e in exps:
                print(f"    {'PASS' if e['passed'] else 'FAIL'}  {e['text']}")
            print()


if __name__ == "__main__":
    main()
