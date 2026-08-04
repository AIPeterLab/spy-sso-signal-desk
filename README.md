# SPY/SSO Signal Desk

Static dashboard for the **SPY SMA200 / volatility-adjusted SSO strategy**.

The signal source is SPY adjusted close. SMA200 bands determine risk-on or risk-off. During risk-on periods, 20-day annualized SPY volatility sets the target to SSO, a 50/50 SSO-SPY blend, or Cash.

## Files

- `index.html` is the live operational dashboard.
- `data/signals.json` is the dashboard snapshot.
- `data/signals.csv` is the full daily model history.
- `data/calendar_cycles.csv` contains 1, 2, 3, 5, and 10-year calendar cycles.
- `data/spread_cycles.csv` contains SPY/SMA200 spread-cycle context.
- `scripts/update_signals.py` downloads adjusted closes and rebuilds the model.
- `scripts/send_pushover_notification.py` sends the post-refresh phone alert.
- `Real_Account_Tracking_System.doc` is the governing operating manual.

## Exact Rules

1. Signal source is SPY adjusted daily close.
2. Risk-on assets are SSO and SPY; the defensive position is Cash.
4. Benchmark is SPY Hold from the same start date and initial value.
5. Buy or hold SSO when SPY adjusted close is strictly above `SMA200 x 1.01`.
6. Sell SSO and move to Cash when SPY adjusted close is strictly below `SMA200 x 0.99`.
7. Between the thresholds, maintain the previous SMA200 trend state.
8. Signals are calculated after the close and affect the next trading day.
9. SSO returns use actual Yahoo Finance adjusted-close data. Synthetic SSO history is not used.
10. When risk-on, target 100% SSO at 20-day annualized SPY volatility of 15% or lower.
11. When risk-on, target 50% SSO / 50% SPY above 15% through 25% volatility.
12. Target Cash when risk-off or when risk-on volatility is above 25%.
13. Volatility threshold crossings after the close create a next-day rebalance signal.
14. VIX and spread-cycle fields are context only. They are not additional trading rules.

## Data And Performance

The updater uses Yahoo Finance chart API adjusted-close data for SPY and SSO, plus VIX index closes for context. It calculates 20-day annualized SPY volatility from the sample standard deviation of adjusted-close returns. Model tracking starts with `$1,000` on SSO's first available date. The benchmark is SPY Hold from the same date and initial value.

Run locally:

```powershell
python scripts/update_signals.py
python -m unittest discover -s tests -v
```

## Automation

GitHub Actions checks at 22:15 and 23:15 UTC and updates only when the New York hour is 6 PM, maintaining an effective 6:15 PM New York schedule through daylight-saving changes.

Pushover uses these repository secrets:

- `PUSHOVER_APP_TOKEN`
- `PUSHOVER_USER_KEY`

## Cloudflare Pages

This repo is ready to deploy as a no-framework Cloudflare Pages static site while keeping the dashboard method aligned with QLD Signal Desk. The daily schedule is centralized in the AIPeterLab Cloudflare Worker, which dispatches this repo's GitHub Actions refresh workflow.

Use these Pages settings:

- Project name: `sso-signal-desk`
- Production branch: `main`
- Framework preset: `None`
- Build command: `exit 0`
- Build output directory: `/`
- Root directory: leave blank / repository root
- Environment variables: none required

Attach the custom domain `sso.aipeterlab.com` in the Cloudflare Pages project. The Cloudflare Worker owns the daily timing, dispatches the GitHub Actions workflow, and that workflow pushes updated data files to `main`; Cloudflare Pages redeploys from GitHub after those pushes.

## Disclaimer

This application is for research and tracking only. It is not financial advice, an offer, or a recommendation to buy or sell securities.
