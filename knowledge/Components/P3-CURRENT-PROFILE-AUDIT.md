# P3 Current-Profile Read-only Audit

Authority: owner-approved ADR-022. Baseline:
`d00bb1ac54951859bb38dcae970235da6664b4e6`. P3/V1 remain PARTIAL.
This is a read-only operator path, not an execution provider or broker unlock.

## Fixed Boundary

`scripts/p3_current_profile_audit.py` defaults to PLAN_ONLY, without credentials or
native imports. Explicit `--audit` reads only the nominated
`backend/private/mt5/p3-operator.json` through the approved loader. Password stays
in SecretStr/in memory, never in output, source, receipt or public documentation.
No .env, other credential stores or normal/operator historical DBs are opened.
Do not create a Windows account or run old provisioning/repair scripts.

`current_profile.py` validates exact configured decimal login/server/DEMO policy
and instrument allowlist before launch. Metadata placeholders may be derived only
after native exact-account DEMO proof; never default currency to USD or fees to0.
There is no account-switch API, ambient SDK initialization or fallback login.
The approved cooperative same-user limitation remains explicit.

Fresh host evidence uses its own schema, not spoofed legacy session-zero flags:
current SID, desktop session, non-admin token, actual worker PID/base Python image,
exclusive owned terminal PID/path, non-reparse paths and restricted ACLs.
Windows PS5 receives only its system module directory, avoiding inherited PS7
security-module autoload failure. Errors contain fixed diagnostic codes only.

The one-worker Windows kernel lock is under ignored `.p3-verification/`. The fixed
new portable path is `backend/private/mt5/current-profile-terminal-v1/terminal64.exe`.
Before first copy, check MetaQuotes Authenticode signature on the fixed public
installation. Copied executable must hash-identically match it. An immutable
startup receipt binds path/hash/current SID/configured identity digest before
first launch. Existing terminal state without this receipt is not adopted. The
previous failed-start `current-profile-terminal/` is preserved, not reused/deleted.
Receipt is ignored runtime metadata, not native account attestation.

Launch only the fixed child in portable mode; verify host before native import,
then exactly one explicit SDK initialize(login,password,server) with60s startup
timeout. No automatic reconnect. Native last_error descriptions are never emitted;
only recognized numeric codes map to fixed diagnostics. In particular -10005 is
IPC timeout, not password rejection. Official sources:
[initialize](https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py),
[last_error](https://www.mql5.com/en/docs/python_metatrader5/mt5lasterror_py).

After successful initialization, prove exact account/server/DEMO, portable data
path, actual currency/company/build/leverage and algo permissions. Then and only
then create/resume a specialized account-bound VerificationLedger, HALT it, collect
native history/inventory/instrument/quote observations and derive ADR-019 unused-
account qualification-start baselines. No original credential config rewrite or
commission fabrication. This tool never creates a P2 approval, reservation,
economic attempt, default-app enablement or HALT reset. It cannot complete P3.
Finally disconnect SDK and stop only its owned, read-only child, including when
SDK shutdown raises. Failed startup retains its receipt for bounded retry.

## User-cancelled Diagnostic Retry

Current actual result: host prechecks pass; IPC timeout while startup Login dialog
visible. We have not proved cancelling it resolves the timeout. User must handle
authentication dialogs; the agent does not click/type in them.

1. User confirms readiness to press Cancel on the initial Login dialog. Do not
   enter credentials, switch accounts or open another terminal.
2. Run from repository root, non-elevated current profile:
   `backend/.venv/Scripts/python.exe -B scripts/p3_current_profile_audit.py --audit`
3. User presses Cancel when the startup dialog appears. SDK still uses the exact
   approved local credentials; no default/ambient login is selected.
4. Inspect sanitized result; stop on any mismatch or unqualified evidence. Do not
   place a trade or interpret READONLY_AUDIT_COMPLETE as operator qualification.
5. Only after actual account/history/metadata/cost evidence and a separately
   fixture-verified current-profile execution composition pass may the ordered
   manual P2/reservation/full-lineage smoke test proceed. Commission unknown
   remains a blocker. Later strategies/WhatsApp/P9 stay behind manual proof.

Stop procedure: this tool has no submission API. On mismatch stop the audit; do
not launch a second worker/terminal. Owned read-only child is stopped on exit. If
cleanup fails, leave execution disabled and inspect exact process metadata before
any retry; never kill an unrelated terminal or claim economic state was closed.

## Evidence Limits

185 focused/1213 broad fixture tests passed, zero protected attempts. These prove
the fixture-safe software contracts, not native broker/account qualification.
Actual demo attestation, economics, risk/cost adequacy, HALT/restart with real
broker evidence, active strategy/WhatsApp routing and full P9 remain unproven.
