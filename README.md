# NexusAI Controlled Rebuild

The rebuild follows `D:/UNI/p learn/NEXUSAI_REBUILD_MASTER_PLAN.md` and the forensic audit
at `D:/quant project/audit-2026-09-08/NexusAI_Forensic_Audit.md`.

**Current runtime: authenticated historical review only. Trading and model training are disabled.**
This is not a completed trading core, a profitable strategy, or production-ready software.

## Run Locally

Use `scripts/start_local.ps1` on Windows. It starts both services hidden, bound to loopback.
The workspace is at http://127.0.0.1:5173 and the API at http://127.0.0.1:8000.
The script creates `backend/private/control_token.txt` when `CONTROL_TOKEN` is absent.
Enter that local token in the workspace. Do not put it in chat, URLs, screenshots, or Git.
An existing environment `CONTROL_TOKEN` takes precedence. Missing tokens never bypass authentication.
The frontend holds the token in memory only; reloading locks it again.

Starting this application does not connect to MT5, close existing positions, enable agents, or train a model.
Existing broker positions must be inspected in MT5 until broker reconciliation is rebuilt.

## Current Source Map

| Responsibility | Source |
|---|---|
| Default application | `backend/main.py` |
| Authenticated review-only API and write allowlist | `backend/core/rebuild/application.py` |
| Immutable typed signal contract | `backend/core/rebuild/contracts.py` |
| Signal parser | `backend/services/signal_parser.py` |
| Separate lifecycle schema and identity ledger | `backend/core/rebuild/ledger.py`, `backend/core/rebuild/migrations/001_lifecycle.sql` |
| Historical source review | `backend/services/chat_import_service.py`, `chat_import_routes.py` |
| Rebuild status and login | `frontend/src/RebuildWorkspace.jsx` |
| Historical review and authorized image loading | `frontend/src/ChatLearningPage.jsx` |
| Retired application, preserved but startup blocked | `backend/legacy_application.py` |

No agent, sentiment vote, synthetic market stream, adaptive weight update, broker adapter,
or model training service is started by the default app. The retired source remains available for
forensic review and isolated regression tests; it is not a supported alternative entry point.

## Evidence And Next Gates

See [Rebuild Status](docs/REBUILD_STATUS.md) for completed checks, incomplete work, and gate dependencies.
Original databases were not merged into the new ledger. Historical reported profits remain unverified.
The ledger has no broker orders, deals, or confirmed outcomes populated by this rebuild.

## Verification

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q --ignore=backend/tests/test_trader_imitation_model.py
cd frontend
npm run build
```

The two legacy model-training tests are deliberately excluded while the no-ML gate applies.
Existing legacy unit tests prove only their isolated behavior, not trading safety.
Private data, secrets, runtime files, and screenshots must stay outside Git and container images.


## Publication copy

Published 5 October 2026 at the owner's request. This is a sanitized source snapshot. Original local Git history and original files remain unchanged. Pictures, videos, binary archives, private/runtime data, dependency folders and credentials are excluded. Notebook outputs, attachments and incidental metadata are removed. Documents are text-only extracts. Media references and redacted configuration may need replacements before running. No claim of successful rerun, production readiness, sole authorship or independent validation is implied.

Research implementation; execution must remain disabled. Runtime and profitability are not established by this publication.
