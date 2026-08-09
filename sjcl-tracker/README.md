# SJCL Tracker

A static, self-updating price chart for **SJCL — Sanjen Jalvidyut Company Limited**
on the Nepal Stock Exchange (NEPSE), hosted free on GitHub Pages.

- `index.html` — the chart viewer (pure HTML/JS, no build step)
- `data/sjcl.json` — the price history, updated automatically
- `scripts/update_data.py` — fetches new data from NEPSE and merges it into `data/sjcl.json`
- `.github/workflows/update-sjcl-data.yml` — runs the fetch script on a schedule

## Setup (one-time)

1. **Create the repo**: push this folder to a new GitHub repo, e.g.
   `github.com/HariPandey41/sjcl-tracker`.

2. **Enable GitHub Pages**:
   Repo → Settings → Pages → Source: **Deploy from a branch** → Branch: `main` / `root` → Save.
   Your site will be live at `https://haripandey41.github.io/sjcl-tracker/`.

3. **Allow the workflow to push commits**:
   Repo → Settings → Actions → General → Workflow permissions →
   select **Read and write permissions** → Save.
   (Without this, the scheduled workflow can fetch data but can't commit it back.)

4. **Populate the first batch of data manually**:
   Repo → Actions tab → "Update SJCL price data" → **Run workflow** (workflow_dispatch button).
   This backfills history from 2018 onward on the first run, then only fetches new days after that.

## How the automatic updates work

- The workflow runs **Sunday–Thursday around 15:15 NPT** (NEPSE's trading days/close time),
  via a GitHub Actions cron schedule.
- Each run calls NEPSE's public price-history endpoint for the `SJCL` ticker only.
- New trading days get appended to `data/sjcl.json`; existing dates are never duplicated.
- If a run fails (e.g. NEPSE's site is unreachable), the existing data file is left untouched —
  nothing breaks, it just tries again next scheduled run.

## Notes

- This relies on the `nepse-scraper` PyPI package, which reads NEPSE's public
  data endpoints. It isn't an official NEPSE API, so if NEPSE changes their site
  structure, the workflow may need a small update to `scripts/update_data.py` —
  check the field names in `FIELD_CANDIDATES` in that file first.
- All data shown is publicly available historical trading data. This tool is for
  personal tracking only and isn't investment advice.
