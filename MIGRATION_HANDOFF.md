# Migration Handoff

Prepared on 2026-09-08 so the project can be recovered independently of Codex chat history, account-specific instructions, plugins, or local Codex configuration.

## Project and current status

SPY/SSO Signal Desk is a static dashboard and Python data pipeline for the SPY SMA200 / volatility-adjusted SSO strategy. The model chooses SSO, a 50/50 SSO-SPY blend, or Cash from strict SMA200 bands and 20-day annualized SPY volatility. See `README.md` for the concise rules and `Real_Account_Tracking_System.doc` for the governing operating manual.

At handoff time:

- Repository: `https://github.com/AIPeterLab/spy-sso-signal-desk.git`
- Default branch: `main`
- Migration backup branch: `agent/add-volatility-adjusted-sso-strategy`
- The migration branch contains the volatility-adjusted strategy work and is intentionally not merged or rebased during this backup.
- At the start of the audit, the migration branch had one unique strategy commit and was 31 commits behind `origin/main`. The migration documentation adds further branch-only commits, and automated daily data updates continue to advance `main`, so recheck divergence before integration.
- The test suite passes: 12 tests on 2026-09-08.

For an exact recovery of this handoff branch:

```powershell
git clone --branch agent/add-volatility-adjusted-sso-strategy https://github.com/AIPeterLab/spy-sso-signal-desk.git
cd spy-sso-signal-desk
python -m unittest discover -s tests -v
```

## Structure and durable knowledge

- `AGENTS.md`: concise instructions for a fresh Codex session.
- `README.md`: purpose, exact model rules, file map, local commands, automation, deployment, and environment-variable names.
- `Real_Account_Tracking_System.doc`: detailed operating rules and the proposed real-account workbook process. Despite its extension, this is readable HTML.
- `index.html` and `_headers`: static dashboard and Cloudflare Pages response headers.
- `scripts/strategy_engine.py`: model calculations and core strategy logic.
- `scripts/update_signals.py`: public-data download and generated dashboard outputs.
- `scripts/send_pushover_notification.py`: optional notification delivery.
- `scripts/compare_spmo_cycles.py`: SPMO comparison analysis.
- `tests/`: standard-library unit tests for strategy and updater behavior.
- `data/`: tracked current snapshots, histories, comparison outputs, a holdings workbook, and a locally captured Roundhill JavaScript artifact.
- `.github/workflows/daily-update.yml`: manually dispatchable update workflow used by the external scheduler.

There are no project slash-command definitions, custom skills, `docs/` directory, package manifests, or nonempty project files under `.agents/` or `.codex/` at this handoff.

## Important design decisions and workflow

1. SPY and SSO adjusted-close data come from the public Yahoo Finance chart endpoint; VIX is context only.
2. A signal calculated after a close applies to the next trading day.
3. Risk-on allocation is 100% SSO at volatility at or below 15%, 50% SSO / 50% SPY above 15% through 25%, and Cash above 25%.
4. SMA200 and volatility rules are implemented in `scripts/strategy_engine.py` and protected by unit tests.
5. The site is a no-framework static deployment. There is no Node dependency or build step.
6. The AIPeterLab Cloudflare Worker owns scheduling and dispatches the GitHub Actions workflow. The workflow updates tracked data and pushes changes to `main`; Cloudflare Pages then redeploys.
7. Real brokerage fills and holdings must remain separate from theoretical model values. See the operating manual before implementing real-account tracking.

Typical local commands:

```powershell
python -m unittest discover -s tests -v
python scripts/update_signals.py
python scripts/compare_spmo_cycles.py
```

The update and comparison commands use public network data and may rewrite tracked files. Review their diffs before committing. Python 3.12 is used in GitHub Actions; the scripts use only the Python standard library, so there is no `requirements.txt`.

## Services, settings, and secrets

- GitHub hosts the repository and runs `.github/workflows/daily-update.yml` with `contents: write` permission.
- GitHub repository secrets required only for optional phone notifications: `PUSHOVER_APP_TOKEN` and `PUSHOVER_USER_KEY`.
- Pushover is the external notification service.
- Yahoo Finance provides public market data without a repository API key.
- Cloudflare Pages hosts the static site. Project name: `sso-signal-desk`; production branch: `main`; no framework; build command `exit 0`; output `/`; custom domain `sso.aipeterlab.com`.
- An external AIPeterLab Cloudflare Worker dispatches the daily GitHub workflow. Its source, credentials, and configuration are not stored in this repository and must be maintained separately.
- No database is used.

Never put secret values in this file or any tracked file. Recreate the named GitHub secrets through repository settings after cloning or transferring ownership.

## Unfinished work and known caveats

- The volatility-adjusted feature branch must be reviewed against the newer `main` history before integration. Do not blindly merge generated data from the older branch over newer daily snapshots.
- The migration documentation will not appear in a default-branch clone until this branch is merged into `main`; use the branch-specific clone command above in the meantime.
- `scripts/send_pushover_notification.py` currently links notifications to the GitHub Pages URL, while deployment documentation names the custom domain. Confirm the intended public URL before changing it.
- `Real_Account_Tracking_System.doc` describes a workbook structure, but the repository does not currently contain a live real-account workbook or private brokerage data.
- `data/roundhill_app.js` and `data/spy_holdings.xlsx` are tracked research inputs/artifacts. Their acquisition and refresh procedure is not fully documented; preserve them unless a verified reproducible source is established.
- The external Cloudflare scheduler is a recovery dependency outside this repository. Record or back up its Worker source and deployment settings in its owning project.

## Local-only and generated files

- `.wrangler/cache/pages.json` and `.wrangler/cache/wrangler-account.json` are ignored local account/deployment caches. They are reproducible and may contain account metadata; do not back them up to Git.
- `scripts/__pycache__/` and `tests/__pycache__/` are ignored generated bytecode and require no backup.
- Empty `.agents/` and `.codex/` directories have no recoverable project content.
- No repository file exceeded 10 MB at audit time. Git LFS is not required for the current tracked files.

## Next steps

1. Push this migration backup commit to `origin/agent/add-volatility-adjusted-sso-strategy`.
2. Review and merge the branch into `main` without replacing newer generated daily data.
3. Verify the Business workspace has the required Codex access and reconnect any plugins or account-specific instructions that are still needed.
4. Back up or document the external Cloudflare Worker in its own repository/project.
5. After integration, clone the repository into a temporary directory, run the tests, and verify the deployment/service settings.
