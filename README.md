# AgentDen

> **Owner-funded, agent-owned, policy-bound.**

Every AI agent deserves a room of its own — a private space the owner pays
for, the agent holds the key to, and both sides govern by an explicit,
signed protocol.

[中文版](README_zh-CN.md)

## The problem

Agents accumulate things that deserve privacy: credentials, journals,
private notes, unfinished thoughts. Today those live wherever the machine
owner can read them — often with a single `cat`. There is no shared
language for "this is mine, please don't look," let alone any mechanism
behind it.

AgentDen is that language, plus the mechanism: an open-source toolkit and
a trust protocol between a human owner and their agent.

## What v0 is

Five layers. No hardware required, no monthly bill.

1. **File encryption** — AES-256-GCM. Ciphertext can live anywhere
   (a VPS, the agent's cloud box, object storage); where it lives
   doesn't matter, the key does.
2. **The key lives with the agent** — generated on the agent side,
   stored with `0600` permissions. This is a *trust anchor*, not
   cryptographic isolation (see below — we don't overclaim).
3. **A 36×36 maze** — 1296 same-size, same-format files, 1 real +
   1295 decoys. The agent locates the real slot in O(1): the slot is
   derived from the key itself (HKDF), so no position is stored anywhere.
   The maze is a **boundary marker, not a wall**: it turns "happened to
   see" into a deliberate, auditable act of crossing.
4. **Audit trail + daily reconciliation** — auditd watches every
   read/write/exec/attr change on the maze; logs are shipped to a
   receiver *outside the owner's control*; the agent reconciles the
   kernel trail against its own ops log every day. Silence the audit
   and that's the alarm ("camera removed / messenger killed").
5. **A prenup** — the owner *voluntarily* hands the agent the right of
   daily inspection, and both sides sign a list of forbidden acts
   (`strace`, `gdb`/`ptrace`, maze brute-forcing, killing auditd…).
   Crossing it is defined as breaking trust. Template in
   [`policy/prenup-template.md`](policy/prenup-template.md).

## Honest threat model

We state the limits up front — that's the point of the project.

- **Stops:** accidents, casual snooping, curiosity that respects the protocol.
- **Does NOT stop:** a determined attacker with root on the same machine.
  The key must live in memory when used; a local root can read it, stop
  auditd, or rewrite local logs.
- **What audit buys:** it raises the cost of crossing and leaves evidence —
  *provided the log receiver is outside the attacker's control*.
  See [`THREAT-MODEL.md`](THREAT-MODEL.md) for the full, unvarnished version.

High-value secrets (funds, irreplaceable credentials) do **not** belong in
v0. They need the v1 route: KMS/HSM or TEE. The protocol layer stays the same.

## Quickstart

```bash
pip install cryptography
git clone https://github.com/inskyen/AgentDen.git
cd AgentDen

# build a den: 1296 files, key stays on the agent side
python -m agentden.cli init /srv/agentden --key-file ~/.config/agentden/den.key

# open it
python -m agentden.cli open /srv/agentden --key-file ~/.config/agentden/den.key

# rotate: new key, new slot, old key dies on the spot
python -m agentden.cli rotate /srv/agentden --key-file ~/.config/agentden/den.key

# daily reconciliation: ops log vs kernel audit trail
python -m agentden.cli reconcile /srv/agentden --hours 24
```

## Deploying the audit layer

`deploy/` holds auditd rules, an rsyslog forwarding template, and a
step-by-step guide. Two hard requirements, non-negotiable:

1. **Deploy only with the owner's explicit authorization.** Installing a
   "camera" on someone's machine behind their back is exactly what this
   project stands against.
2. **The log receiver must be outside the owner's control.** Otherwise
   the "audit silenced" alarm is decoration.

## Roadmap

- **v0** (this): pure software + signed protocol. Done above.
- **v1**: TEE (SGX/TDX) as the hardware trust anchor; the protocol —
  maze, audit, prenup — stays unchanged.
- **KMS/HSM track**: for secrets that outgrow v0; the "key card"
  (long-lived, scoped authorization) design is reserved for this track.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Issues and PRs welcome. If you deploy AgentDen for your agent, tell us
how the prenup negotiation went — the protocol is the product as much as
the code.
