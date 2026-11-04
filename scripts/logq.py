"""Read Venture CRM's JSON log without needing grep or jq (works the same on Windows, macOS and Linux).

Run from the project folder (the one with manage.py):

    python scripts/logq.py --failed            # the last 10 requests that ended in a 5xx error
    python scripts/logq.py 105e4d00498343b4    # every line for one request_id (a user's "Reference code")
    python scripts/logq.py --last 20           # the last 20 log lines, any kind

It reads logs/venture-crm.jsonl plus its rotated copies (.1 ... .5), oldest first.
Set VENTURE_CRM_LOG_DIR to read a different folder.
"""

import argparse
import json
import os
import sys
from pathlib import Path

LOG_DIR = Path(os.environ.get("VENTURE_CRM_LOG_DIR", Path(__file__).resolve().parent.parent / "logs"))
LEADING = ("ts", "level", "logger", "event", "request_id")


def log_files():
    rotated = sorted(LOG_DIR.glob("venture-crm.jsonl.*"), key=lambda p: int(p.suffix[1:]), reverse=True)
    current = LOG_DIR / "venture-crm.jsonl"
    return rotated + ([current] if current.exists() else [])


def read_lines():
    for path in log_files():
        with path.open(encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if raw:
                    yield json.loads(raw)


def show(line):
    extra = {k: v for k, v in line.items() if k not in LEADING}
    if "stack" in extra:  # keep the last line of the traceback, which names the error
        extra["stack"] = "... " + extra["stack"].strip().splitlines()[-1]
    details = "  ".join(f"{k}={json.dumps(v)}" for k, v in extra.items())
    print(f"{line['ts']}  {line['level']:<7} {line['event']:<24} rid={line['request_id']}  {details}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("request_id", nargs="?", help="show every line for this request_id / reference code")
    parser.add_argument("--failed", action="store_true", help="list recent requests that ended with a 5xx status")
    parser.add_argument("--last", type=int, default=10, help="how many lines/requests to show (default 10)")
    args = parser.parse_args()

    if not log_files():
        sys.exit(f"No log files found in {LOG_DIR}. Is the server running from this folder?")

    lines = list(read_lines())
    if args.request_id:
        matches = [line for line in lines if line["request_id"] == args.request_id]
        if not matches:
            sys.exit(f"No lines with request_id {args.request_id} in {LOG_DIR}.")
        selected = matches
    elif args.failed:
        selected = [l for l in lines if l["event"] == "request.end" and l.get("status", 0) >= 500][-args.last :]
        if not selected:
            print("No failed (5xx) requests in the log.")
    else:
        selected = lines[-args.last :]
    for line in selected:
        show(line)


if __name__ == "__main__":
    main()
