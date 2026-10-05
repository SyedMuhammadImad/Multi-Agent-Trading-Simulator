"""Operator-only --audit: fixed-account read connection, never an order or unlock."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    if not args.audit:
        report = dict(status='PLAN_ONLY', broker_connected=False, broker_actions=0,
                      broker_execution='HARD_DISABLED', live='LOCKED')
    else:
        try:
            from core.rebuild.current_profile import readonly_audit
            report = readonly_audit()
        except Exception as error:
            import re
            from core.rebuild.operator_verification import OperatorBlocked
            code = str(error) if isinstance(error, OperatorBlocked) else 'CURRENT_PROFILE_PRECONNECTION_GATE_FAILED'
            if not re.fullmatch(r'[A-Z0-9_]+', code):
                code = 'CURRENT_PROFILE_PRECONNECTION_GATE_FAILED'
            report = dict(status='NOT_QUALIFIED', blocker=code,
                          broker_actions=0, broker_execution='HARD_DISABLED', live='LOCKED')
    print(json.dumps(report, sort_keys=True))
    return 0 if report['status'] in {'PLAN_ONLY', 'READONLY_AUDIT_COMPLETE'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
