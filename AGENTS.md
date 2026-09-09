# Codex Project Instructions

## Purpose and sources of truth

- This repository operates the SPY SMA200 / volatility-adjusted SSO signal dashboard.
- Read `README.md` for the system overview and commands.
- Treat `Real_Account_Tracking_System.doc` as the governing operating manual. It is HTML content stored with a `.doc` extension.
- Read `MIGRATION_HANDOFF.md` for repository recovery, services, branch context, and current caveats.

## Working rules

- Preserve the exact strategy semantics in `README.md`, the operating manual, and `scripts/strategy_engine.py`: adjusted closes, strict SMA200 bands, next-trading-day application, and the 15%/25% volatility allocation thresholds.
- Do not change live strategy rules without explicit user approval, new tests, and matching documentation updates.
- Run `python -m unittest discover -s tests -v` after Python changes.
- `scripts/update_signals.py` requires public network access to Yahoo Finance and rewrites the generated signal and cycle files listed in `README.md`. Do not run it merely to format or validate unrelated changes.
- Keep generated data changes separate and review their dates and diffs before committing.
- Never commit `.env` files, credentials, tokens, API keys, private keys, account cache files, or secret values. Only the environment-variable names `PUSHOVER_APP_TOKEN` and `PUSHOVER_USER_KEY` belong in documentation.
- Do not commit `.wrangler/`, Python bytecode, or test caches.
- The GitHub Actions workflow is dispatched by an external AIPeterLab Cloudflare Worker and can also be run manually. Cloudflare Pages deploys the static repository; no local build step or package install is required.
- Do not force-push or discard local changes. Confirm the active branch and its upstream before pushing.
