"""
Fetches SJCL (Sanjen Jalvidyut Company Limited) daily price history from NEPSE
and merges it into data/sjcl.json, keeping one record per trading date.

Run manually:
    python scripts/update_data.py

Designed to run unattended in GitHub Actions on a schedule. It is safe to
run repeatedly - existing dates are never duplicated, and if the fetch
fails for any reason the existing data file is left untouched.
"""

import json
import os
import sys
from datetime import date, timedelta

TICKER = "SJCL"
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sjcl.json")

# First run has no history yet, so backfill from here.
BACKFILL_START = "2018-01-01"

# Field names NEPSE's API has been observed to use, in priority order.
# The script tries each candidate until one matches, so if NEPSE tweaks
# their schema slightly this keeps working without edits.
FIELD_CANDIDATES = {
    "date": ["businessDate", "businessdate", "date"],
    "open": ["openPrice", "openprice", "open"],
    "high": ["highPrice", "maxPrice", "highprice", "high"],
    "low": ["lowPrice", "minPrice", "lowprice", "low"],
    "close": ["closePrice", "closeprice", "lastTradedPrice", "close"],
    "volume": ["totalTradedQuantity", "totaltradedquantity", "volume"],
}


def pick(record, keys):
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return None


def normalize(record):
    row = {field: pick(record, keys) for field, keys in FIELD_CANDIDATES.items()}
    if not row["date"] or row["close"] is None:
        return None
    # Dates sometimes arrive as "2025-08-09T00:00:00" - keep just the date part.
    row["date"] = str(row["date"])[:10]
    for numeric_field in ("open", "high", "low", "close", "volume"):
        if row[numeric_field] is not None:
            try:
                row[numeric_field] = float(row[numeric_field])
            except (TypeError, ValueError):
                row[numeric_field] = None
    return row


def load_existing():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    return []


def main():
    from nepse_scraper import NepseScraper

    existing = load_existing()
    by_date = {row["date"]: row for row in existing}

    if existing:
        last_date = max(by_date.keys())
        start_date = (date.fromisoformat(last_date) + timedelta(days=1)).isoformat()
    else:
        start_date = BACKFILL_START

    end_date = date.today().isoformat()

    if start_date > end_date:
        print(f"Already up to date (last record: {end_date}). Nothing to fetch.")
        return

    print(f"Fetching {TICKER} price history from {start_date} to {end_date}...")

    try:
        client = NepseScraper()
        raw_records = client.get_ticker_price_history(TICKER, start_date, end_date)
    except Exception as exc:  # noqa: BLE001 - we want to fail soft in CI
        print(f"Fetch failed: {exc}")
        print("Leaving existing data file untouched.")
        sys.exit(0 if existing else 1)

    if isinstance(raw_records, dict):
        raw_records = raw_records.get("content", raw_records.get("data", []))

    added = 0
    for record in raw_records or []:
        row = normalize(record)
        if row and row["date"] not in by_date:
            by_date[row["date"]] = row
            added += 1

    merged = sorted(by_date.values(), key=lambda r: r["date"])

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    print(f"Added {added} new record(s). Total records: {len(merged)}.")


if __name__ == "__main__":
    main()
