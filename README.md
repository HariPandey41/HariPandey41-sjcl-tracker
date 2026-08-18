# SJCL Tracker

A static, self-updating price tracker for **SJCL — Sanjen Jalvidhyut Company Limited** on the Nepal Stock Exchange (NEPSE). The site is plain HTML and JavaScript, so GitHub Pages can serve it directly from the repository root without a build step.

## What was fixed

The original repository contained the web page at the repository root but stored `data/sjcl.json`, the updater, and the dependency file inside a nested `sjcl-tracker/` directory. The page therefore requested a data file that did not exist at the URL GitHub Pages served. The scheduled workflow was also missing from `.github/workflows/`, the dependency file was empty, and the extractor attempted to use `nepse_scraper` without installing it.

The repository now has one canonical root layout:

| Path | Purpose |
| --- | --- |
| `index.html` | GitHub Pages dashboard and Chart.js price chart |
| `data/sjcl.json` | Normalized SJCL daily OHLCV history used by the page |
| `scripts/update_data.py` | Fetches, normalizes, merges, and atomically writes data |
| `requirements.txt` | Pinned `nepse-scraper` dependency |
| `.github/workflows/update-sjcl-data.yml` | Manual and scheduled data refresh workflow |

The populated data file contains the currently available records returned by NEPSE’s public historical endpoint. Each row contains `date`, `open`, `high`, `low`, `close`, and `volume`. NEPSE currently returns the latest 224 SJCL trading records for this endpoint; the updater will preserve all existing rows and append new records as they become available.

## One-time GitHub settings

GitHub Pages should be configured from **Settings → Pages → Build and deployment → Deploy from a branch**, using the `main` branch and the `/ (root)` folder. The site URL will be:

`https://haripandey41.github.io/HariPandey41-sjcl-tracker/`

The repository’s Actions setting should allow workflows to write repository contents. Open **Settings → Actions → General → Workflow permissions**, select **Read and write permissions**, and save. The workflow also declares `permissions: contents: write`, but the repository-level setting must not restrict that permission.

After pushing this change, open **Actions → Update SJCL price data → Run workflow** once. That manual run confirms that the workflow can access NEPSE, write `data/sjcl.json`, and commit a refresh. Subsequent updates run Sunday through Thursday at 15:15 Nepal time, which is 09:30 UTC.

## Local run

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/update_data.py
```

The current NEPSE server certificate chain may require the updater’s default `NEPSE_VERIFY_SSL=false` behavior. This is intentional for compatibility with the public endpoint used by `nepse-scraper`. If the runner has a complete certificate chain, set `NEPSE_VERIFY_SSL=true` to enable verification.

The updater is idempotent: dates are used as keys, duplicate trading days are replaced rather than duplicated, and the existing JSON file is preserved if NEPSE is unavailable or returns no valid records. The optional environment variables `SJCL_BACKFILL_START`, `SJCL_PAGE_SIZE`, and `SJCL_END_DATE` can be used for controlled local tests.

## Disclaimer

The data is public market information for personal tracking. It is not investment advice.
