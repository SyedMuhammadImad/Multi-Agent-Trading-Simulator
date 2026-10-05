# ADR-022 - Cooperative Current-Profile DEMO Boundary

Status: **ACCEPTED**, 2026-10-05. Owner explicitly approved the precise question:
"Approve cooperative current-profile DEMO boundary".

## Decision

Replace the withdrawn dedicated-user/session-zero operator arrangement with an
explicitly cooperative boundary in the owner's current, non-elevated Windows
profile. Do not create another Windows account, deploy the old SYSTEM service or
silently reuse its SID/receipts. This supersedes those host requirements in
ADR-019/020, not qualification-start equity semantics or any P2 numerical policy.

The replacement requires a separate pristine portable terminal, exact configured
DEMO account/server, one NexusAI worker, fixed private credential boundary,
separate verification state, validated executable identity, current-user/session
binding and account checks before/after reads and immediately before submission.
LIVE remains locked. No default/ambient account selection, saved-login fallback,
login-switch API, arbitrary terminal path or automatic reconnect is permitted.
Account/terminal changes, foreign terminal/process ownership, stale/missing
evidence, ambiguous state or failed HALT/P2 checks abort and retain evidence.
No ordinary app, research strategy or WhatsApp path gains authority from this ADR.

## Accepted limitation

The owner trusts themselves and other software running as the current user not to
switch the designated terminal's account or interfere with the worker. No live
credentials may be used in that terminal. This is NOT the former separate-user
OS isolation or protection against same-user hostile software/administrator access.
MT5 order_send has no atomic account/login field; pre-send attestation alone does
not prove safety against an uncontrolled concurrent account switch. Never label
the cooperative path as an unconditional no-live-route guarantee.

Official API evidence reviewed 2026-10-05:
https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py
https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py

## Ordered gate

Reconcile dirty work, fix/retest the reproduced storage regression, and commit
the non-executing integration baseline before native qualification. Then qualify
the replacement path with fixtures and actual operator evidence. Account history,
cost evidence, minimum size, P2/HALT, reservations and exact lineage remain
mandatory. Unknown commission is not zero. Baseline approval and this ADR do not
prove a connected DEMO account, authorize a P2 bypass or complete V1/P3/P9.
