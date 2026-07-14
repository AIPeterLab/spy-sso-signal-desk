# SPY/SSO Signal Desk

Static dashboard for the **SPY SMA200 SSO -> Cash strategy**.

The signal source is SPY adjusted close. The model holds SSO while SPY remains above the upper SMA200 band, moves to Cash below the lower SMA200 band, and holds the prior state inside the band.

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
2. Invested asset is SSO.
3. Defensive position is Cash.
4. Benchmark is SPY Hold from the same start date and initial value.
5. Buy or hold SSO when SPY adjusted close is strictly above `SMA200 x 1.01`.
6. Sell SSO and move to Cash when SPY adjusted close is strictly below `SMA200 x 0.99`.
7. Between the thresholds, maintain the previous SSO or Cash position.
8. Signals are calculated after the close and affect the next trading day.
9. SSO returns use actual Yahoo Finance adjusted-close data. Synthetic SSO history is not used.
10. VIX and spread-cycle fields are context only. They are not additional trading rules.

## Data And Performance

The updater uses Yahoo Finance chart API adjusted-close data for SPY and SSO, plus VIX index closes for context. Model tracking starts with `$1,000` on SSO's first available date. The benchmark is SPY Hold from the same date and initial value.

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

This repo is ready to deploy as a no-framework Cloudflare Pages static site while keeping the dashboard method and GitHub Actions refresh workflow aligned with QLD Signal Desk.

Use these Pages settings:

- Project name: `sso-signal-desk`
- Production branch: `main`
- Framework preset: `None`
- Build command: `exit 0`
- Build output directory: `/`
- Root directory: leave blank / repository root
- Environment variables: none required

Attach the custom domain `sso.aipeterlab.com` in the Cloudflare Pages project. The existing GitHub Actions workflow owns the daily data refresh and pushes updated data files to `main`; Cloudflare Pages redeploys from GitHub after those pushes.

## Disclaimer

This application is for research and tracking only. It is not financial advice, an offer, or a recommendation to buy or sell securities.
