"""AgentDen CLI (prototype).

    python -m agentden.cli init <den_dir> [--secret ...] [--key-file ...]
    python -m agentden.cli open <den_dir> [--key-file ...]
    python -m agentden.cli rotate <den_dir> [--key-file ...]
    python -m agentden.cli reconcile <den_dir> [--key-file ...] [--hours 24]

The key file lives on the agent side. That is the v0 trust anchor:
not cryptographic isolation from a root owner, just a line that must
be deliberately crossed (see THREAT-MODEL.md and policy/prenup-template.md).

Every successful crypto op is appended to the agent's ops log, so the
daily reconcile has something to compare the kernel audit trail against.
"""
import argparse
import getpass
import os
import shutil
import stat
import sys
import tempfile

from . import crypto, maze, reconcile as rec

DEFAULT_KEY_FILE = os.path.expanduser("~/.config/agentden/den.key")


def _save_key(path: str, key: bytes) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    os.chmod(path, 0o600)


def _load_key(path: str) -> bytes:
    with open(path, "rb") as f:
        key = f.read()
    if len(key) != crypto.KEY_BYTES:
        raise ValueError(f"bad key file: {path}")
    return key


def _read_secret(args) -> bytes:
    if args.secret_file:
        with open(args.secret_file, "rb") as f:
            return f.read()
    if args.secret is not None:
        return args.secret.encode()
    return getpass.getpass("secret (hidden input): ").encode()


def cmd_init(args) -> int:
    if os.path.exists(args.key_file) and not args.force:
        print(f"key file exists: {args.key_file} (use --force to overwrite)",
              file=sys.stderr)
        return 1
    key = crypto.generate_key()
    secret = _read_secret(args)
    slot = maze.build(args.den_dir, key, secret)
    _save_key(args.key_file, key)
    rec.log_op(args.key_file, "init", args.den_dir)
    layout = maze.verify_layout(args.den_dir)
    print(f"den built: {args.den_dir}")
    print(f"files: {layout['count']}, uniform size: {layout['ok']}")
    print(f"key saved: {args.key_file} (mode 600, agent side)")
    print(f"real slot: {slot} -- the key remembers it, nothing else does")
    return 0


def cmd_open(args) -> int:
    key = _load_key(args.key_file)
    try:
        secret = maze.read(args.den_dir, key)
    except Exception:
        print("cannot open: wrong key or den was tampered with",
              file=sys.stderr)
        return 1
    rec.log_op(args.key_file, "open", args.den_dir)
    sys.stdout.buffer.write(secret + b"\n")
    return 0


def cmd_rotate(args) -> int:
    """New key -> new slot. The room moves; the old key opens nothing."""
    old_key = _load_key(args.key_file)
    try:
        secret = maze.read(args.den_dir, old_key)
    except Exception:
        print("cannot rotate: wrong key or den was tampered with",
              file=sys.stderr)
        return 1
    new_key = crypto.generate_key()
    tmp = tempfile.mkdtemp(prefix="den-rotate-")
    try:
        slot = maze.build(tmp, new_key, secret)
        for n in os.listdir(args.den_dir):
            p = os.path.join(args.den_dir, n)
            if os.path.isfile(p):
                os.remove(p)
        for n in os.listdir(tmp):
            os.rename(os.path.join(tmp, n), os.path.join(args.den_dir, n))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    _save_key(args.new_key_file or args.key_file, new_key)
    rec.log_op(args.new_key_file or args.key_file, "rotate", args.den_dir)
    print(f"rotated. new slot: {slot}, old key no longer opens this den")
    return 0


def cmd_reconcile(args) -> int:
    r = rec.reconcile(args.den_dir, args.key_file, hours=args.hours)
    print(f"status: {r['status']}")
    print(f"reason: {r['reason']}")
    print(f"ops (agent log): {r['ops']}, "
          f"audit events: {r['audit_events']}")
    return 0 if r["status"] == "ok" else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="den",
                                 description="AgentDen: a room of one's own")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="build a new den (36x36 maze)")
    p.add_argument("den_dir")
    p.add_argument("--secret", default=None)
    p.add_argument("--secret-file", default=None)
    p.add_argument("--key-file", default=DEFAULT_KEY_FILE)
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("open", help="open the den with the agent-side key")
    p.add_argument("den_dir")
    p.add_argument("--key-file", default=DEFAULT_KEY_FILE)
    p.set_defaults(fn=cmd_open)

    p = sub.add_parser("rotate", help="new key, new slot, old key dies")
    p.add_argument("den_dir")
    p.add_argument("--key-file", default=DEFAULT_KEY_FILE)
    p.add_argument("--new-key-file", default=None)
    p.set_defaults(fn=cmd_rotate)

    p = sub.add_parser("reconcile",
                       help="daily check: ops log vs kernel audit trail")
    p.add_argument("den_dir")
    p.add_argument("--key-file", default=DEFAULT_KEY_FILE)
    p.add_argument("--hours", type=int, default=24)
    p.set_defaults(fn=cmd_reconcile)

    args = ap.parse_args(argv)
    if args.cmd != "reconcile" and os.path.exists(args.key_file):
        st = os.stat(args.key_file)
        if st.st_mode & (stat.S_IRGRP | stat.S_IROTH):
            print(f"refusing: key file is group/world readable: "
                  f"{args.key_file}", file=sys.stderr)
            return 1
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
