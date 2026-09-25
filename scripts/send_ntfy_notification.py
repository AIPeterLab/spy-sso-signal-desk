#!/usr/bin/env python3
"""Send the latest SPY/SSO signal to the shared AIPeterLab ntfy topic."""

import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_PATH = ROOT / "data" / "signals.json"
NTFY_URL = "https://ntfy.sh/aipeterlab-market-alert-1"
DASHBOARD_URL = "https://aipeterlab.github.io/spy-sso-signal-desk/"


def main() -> None:
    with SIGNALS_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    summary = data["summary"]
    message = "\n".join(
        [
            f"Market date: {summary['date']}",
            f"Action: {summary['current_action']}",
            f"SPY: ${summary['spy_close']:.2f}",
            f"SSO: ${summary['sso_close']:.2f}",
            f"20-day SPY volatility: {summary['spy_20d_volatility']:.2%}",
            f"Target: {summary['position']}",
            f"SPY/SMA200 spread: {summary['spread']:+.2%}",
            summary["reason"],
        ]
    ).encode("utf-8")

    request = urllib.request.Request(
        NTFY_URL,
        data=message,
        headers={
            "Title": f"SPY/SSO: Hold {summary['position']}",
            "Priority": "high",
            "Click": DASHBOARD_URL,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)

    if result.get("event") != "message" or result.get("topic") != "aipeterlab-market-alert-1":
        raise RuntimeError(f"ntfy rejected the notification: {result}")

    print(f"ntfy notification sent for market date {summary['date']}.")


if __name__ == "__main__":
    main()
