# Current-Profile Operator Audit - 2026-10-05

Status: WAITING_FOR_USER; P3/V1 PARTIAL; broker HARD_DISABLED/LIVE LOCKED.
Branch core-rebuild. Initial HEAD d98b9c5; clean integration baseline
`d00bb1ac54951859bb38dcae970235da6664b4e6`. Owner accepted ADR-022 explicitly.

## Implemented And Tested

- Separate cooperative current-profile receipt schema, non-admin current SID/
  desktop session/worker PID checks; no old Windows account/SYSTEM attestor.
- Fixed signed public binary -> pristine private portable terminal, immutable
  startup receipt and one-worker lease. No arbitrary terminal/credential/DB path.
- Strict configured account binding, native DEMO checks and sanitized diagnostics;
  no economic API. HALT/qualification-start bootstrap only after attestation.
-185 focused tests pass (22.04s);1213 broad pass (221.72s),2333 upstream warnings.
  Sensitive/operator attempts0 and forbidden native/runtime modules[] in tests.
  Original Windows registry failure reproduced and repaired without test weakening.

## Actual Operator Observations

Exact nominated private configuration exists; password supplied. Four non-secret
metadata placeholders remain (currency/company/source), intended for native
derivation, not grounds to request the existing password again. No secret values
were emitted or copied into public files; original configuration not rewritten.

First prechecks failed before native initialization: PS5 security module autoload
and venv launcher vs actual worker process image. Both diagnosed using metadata,
fixed, covered by tests. ACL/identity conditions were not bypassed or fabricated.
Subsequent actual current-identity/session/non-admin/exclusive-terminal/restricted-
ACL checks passed; MetaQuotes signature and binary equality checks passed.

Three explicit native initialize attempts returned False, zero order calls:
initial10s attempt preceded numeric diagnostic and was mislabeled authentication;
two later60s attempts returned native -10005 (IPC timeout), not -6 authorization.
No auto reconnect/submission retry occurred. Credentials were not shown. Native
descriptions were not emitted. Dedicated startup terminal has immutable receipt.
The original first failed-start terminal was preserved, not silently adopted.

Read-only UI accessibility inspection during the last attempt found startup Login
dialog (Login/Password/Server/OK/Cancel controls). No credential values/screenshots
emitted, no UI inputs performed. Its causal role in IPC timeout is INFERENCE until
a user-cancelled retry succeeds. User asked to confirm readiness and press Cancel
during next audit. Do not automate authentication or call this wrong-password proof.

Finally SDK shutdown and owned-child stop completed; post-check MT5 process count0.
No broker account was attested/connected successfully. No economic attempt, order,
deal, position, reservation, approval or account-bound verification ledger created.
No normal/operator historical DB was opened. Fixed ignored startup receipt/worker
lock are provisioning state only, not broker evidence. Git ignore checked for
nominated private config/terminal and `.p3-verification/` receipt; all ignored.

## Outstanding Ordered Gates

1. User-cancelled bounded read-only startup diagnostic; prove actual native DEMO
   binding/history/metadata and unused-account qualification baselines.
2. Independently qualified commission/cost evidence and current P2 risk context.
3. Fixture-tested current-profile execution composition; first minimum-volume
   MANUAL full P1/P2/P3 lineage, rejection, HALT/restart/native reconciliation.
4. Only after manual proof: genuine closed-bar strategy operational routing,
   authorized current WhatsApp delivery, broker-backed P9 and operational services.

No numerical policy/strategy/ML/data change, new account, live access or order.
P3 operator, P9 and V1 are not complete. Fixture previews/build passed but stopped;
neither frontend nor backend is currently verified as a broker-backed service.
