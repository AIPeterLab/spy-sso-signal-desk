# SSO Signal Desk

Public dashboard for the SPY SMA200 signal / SSO-or-Cash strategy.

Live dashboard: `https://aipeterlab.github.io/spy-sso-signal-desk/`

Cloudflare custom domain target: `https://sso.aipeterlab.com/`

## Strategy

- Signal source: SPY adjusted daily close.
- Indicator: SPY 200-day simple moving average.
- Invested asset: SSO.
- Defensive position: Cash.
- Benchmark: SPY Hold.
- Buy or hold SSO when SPY adjusted close is greater than `SMA200 × 1.01`.
- Sell SSO and move to Cash when SPY adjusted close is less than `SMA200 × 0.99`.
- Between the thresholds, maintain the previous position.
- Signals are calculated after the close and affect the next trading day.
- SSO returns use actual Yahoo Finance adjusted-close data. Synthetic SSO history is not used.
- SPY/SMA200 spread-cycle analysis is informational only.
- VIX is shown as market context only. It is not an additional trading rule.

## Dashboard Views

The site includes an operational dashboard, searchable daily data, browser-local real-account tracking, an editable trade log, full calendar-year cycle comparisons, spread cycles, complete operating rules, and import/export settings.

Real brokerage inputs are stored in the browser with `localStorage`. They do not alter the model ledger or the published signal data. Actual fill prices, shares, and cash remain separate from theoretical adjusted-close model values.

## Data Files

- `data/signals.json` powers the full application.
- `data/signals.csv` contains the daily model ledger.
- `data/calendar_cycles.csv` contains 1, 2, 3, 5, and 10-year calendar cycles.
- `data/spread_cycles.csv` contains every SSO buy-to-sell spread cycle.

The application can also import a replacement JSON model file or a daily CSV from the Settings and Daily Data views.

## Local Update and Tests

```powershell
python scripts/update_signals.py
python -m unittest discover -s tests -v
```

The updater uses the Yahoo Finance chart API with adjusted-close history for SPY and SSO, plus VIX index closes for dashboard context.

## Daily Automation

`.github/workflows/daily-update.yml` runs at 6:15 PM in the `America/New_York` timezone. It:

1. Runs the unit tests.
2. Downloads fresh SPY and SSO adjusted-close data plus VIX context data.
3. Rebuilds JSON and CSV outputs.
4. Automatically commits changed data.
5. Sends an optional Pushover phone notification.

The non-zero schedule minute reduces start-of-hour scheduling congestion.

## Pushover Notifications

Add these GitHub repository secrets under **Settings → Secrets and variables → Actions**:

- `PUSHOVER_APP_TOKEN`
- `PUSHOVER_USER_KEY`

If both secrets are present, the workflow sends the latest market date, model position, action, SPY and SSO prices, spread, signal reason, and a link to the public dashboard. If they are absent, the refresh still succeeds and the notification step is skipped.

## Deployment

The site is static and can be deployed from the default branch and repository root. No build step is required.

## Cloudflare Pages

This repo is ready to deploy as a no-framework Cloudflare Pages static site while keeping the dashboard method and GitHub Actions refresh workflow unchanged.

Use these Pages settings:

- Project name: `sso-signal-desk`
- Production branch: `main`
- Framework preset: `None`
- Build command: `exit 0`
- Build output directory: `/`
- Root directory: leave blank / repository root
- Environment variables: none required

After the first Pages deployment, attach the custom domain `sso.aipeterlab.com` in the Cloudflare Pages project. The existing GitHub Actions workflow should continue to own the daily data refresh and push updated `data/signals.json`, `data/signals.csv`, `data/calendar_cycles.csv`, and `data/spread_cycles.csv` to `main`; Cloudflare Pages will redeploy from GitHub after those pushes.

## Important Distinction

The model assumes adjusted-close returns and exact close-to-next-day timing. Real-account tracking uses actual brokerage shares, cash, and fill prices. Differences are expected and must be reconciled; model values must never overwrite brokerage records.

## Disclaimer

This application is for research and tracking only. It is not financial advice, an offer, or a recommendation to buy or sell securities.
