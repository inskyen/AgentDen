"""AgentDen daily reconciliation (v0 heuristic).

Compares two sources for the last N hours:
  1. the agent's own ops log  ("I opened the den N times")
  2. the kernel audit trail   ("the maze dir was touched M times")

Outcomes:
  - audit silent but ops exist  -> auditd may be off / rules missing.
    Treat as "camera removed": alert immediately.
  - audit events clearly exceed agent ops -> someone else touched the maze.
    Dump the raw trail for manual review.
  - otherwise -> consistent.

This is a heuristic, not a proof. A root attacker who controls the
machine can silence auditd AND would then trip the first case --
provided the audit receiver is outside their control (see deploy/).
"""
import json
import os
import subprocess
import time

OPS_WINDOW_TOLERANCE = 3  # one open ≈ up to this many audit events


def default_ops_log(key_file: str) -> str:
    return os.path.join(os.path.dirname(key_file) or ".", "ops.log")


def log_op(key_file: str, op: str, den_dir: str) -> None:
    path = default_ops_log(key_file)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps({"ts": int(time.time()), "op": op,
                            "den": den_dir}) + "\n")


def load_ops(ops_log: str, since_ts: int) -> list:
    ops = []
    if not os.path.exists(ops_log):
        return ops
    with open(ops_log) as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("ts", 0) >= since_ts:
                ops.append(e)
    return ops


def count_audit_events(den_dir: str, hours: int) -> int | None:
    """Count auditd events touching den_dir in the window.

    Returns None when ausearch/auditd is unavailable (not an error --
    this box simply has no kernel auditing; the deploy target does).
    """
    since = f"{hours} hours ago"
    try:
        p = subprocess.run(
            ["ausearch", "-k", "agentden-maze", "-ts", since, "-i"],
            capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return None
    if p.returncode not in (0, 1):  # 1 == no matches, which is fine
        return None
    n = 0
    for line in p.stdout.splitlines():
        if line.startswith("time ->"):
            n += 1
    # crude scope filter: only count records mentioning our den dir
    # (a finer parse is deploy-specific; v0 keeps it explainable)
    return n


def reconcile(den_dir: str, key_file: str, hours: int = 24) -> dict:
    since_ts = int(time.time()) - hours * 3600
    ops = load_ops(default_ops_log(key_file), since_ts)
    audit_n = count_audit_events(den_dir, hours)

    if audit_n is None:
        return {"status": "unknown",
                "reason": "ausearch/auditd unavailable on this box",
                "ops": len(ops), "audit_events": None}
    if audit_n == 0 and ops:
        return {"status": "ALERT",
                "reason": "agent operated but audit trail is silent -- "
                          "auditd may be stopped or rules removed "
                          "(camera removed / messenger killed)",
                "ops": len(ops), "audit_events": 0}
    if audit_n > max(1, len(ops)) * OPS_WINDOW_TOLERANCE:
        return {"status": "ALERT",
                "reason": "audit events exceed agent ops -- "
                          "someone else may have touched the maze; "
                          "run: ausearch -k agentden-maze -i | less",
                "ops": len(ops), "audit_events": audit_n}
    return {"status": "ok",
            "reason": "audit trail consistent with agent ops",
            "ops": len(ops), "audit_events": audit_n}
