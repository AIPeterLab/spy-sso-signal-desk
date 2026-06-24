#!/usr/bin/env python3
"""Send the latest SPY/SSO signal to Pushover when secrets are configured."""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_PATH = ROOT / "data" / "signals.json"
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"
DASHBOARD_URL = "https://aipeterlab.github.io/spy-sso-signal-desk/"


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    with SIGNALS_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    summary = data["summary"]
    body = urllib.parse.urlencode(
        {
            "token": required_env("PUSHOVER_APP_TOKEN"),
            "user": required_env("PUSHOVER_USER_KEY"),
            "title": f"SPY/SSO: Hold {summary['position']}",
            "message": "\n".join(
                [
                    f"Market date: {summary['date']}",
                    f"Action: {summary['current_action']}",
                    f"SPY: ${summary['spy_close']:.2f}",
                    f"SSO: ${summary['sso_close']:.2f}",
                    f"SPY/SMA200 spread: {summary['spread']:+.2%}",
                    summary["reason"],
                ]
            ),
            "url": DASHBOARD_URL,
            "url_title": "Open SPY/SSO dashboard",
            "priority": "0",
        }
    ).encode("utf-8")
    request = urllib.request.Request(PUSHOVER_URL, data=body, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("status") != 1:
        raise RuntimeError(f"Pushover rejected the notification: {result}")
    print(f"Pushover notification sent for market date {summary['date']}.")


if __name__ == "__main__":
    main()
