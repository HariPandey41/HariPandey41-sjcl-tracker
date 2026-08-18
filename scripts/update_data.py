"""Fetch and persist SJCL daily OHLCV history from NEPSE.

The script is safe to run repeatedly. It upserts records by trading date,
handles the paginated response returned by the current NEPSE API, and leaves
the existing data file unchanged when a fetch fails or returns no valid rows.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from nepse_scraper import NepseScraper

TICKER = "SJCL"
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sjcl.json"
BACKFILL_START = os.getenv("SJCL_BACKFILL_START", "2019-08-06")
PAGE_SIZE = int(os.getenv("SJCL_PAGE_SIZE", "500"))

FIELD_CANDIDATES = {
    "date": ("businessDate", "businessdate", "date", "tradeDate"),
    "open": ("openPrice", "openprice", "open"),
    "high": ("highPrice", "maxPrice", "highprice", "high"),
    "low": ("lowPrice", "minPrice", "lowprice", "low"),
    "close": ("closePrice", "closeprice", "lastTradedPrice", "close"),
    "volume": ("totalTradedQuantity", "totaltradedquantity", "volume"),
}


def pick(record: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return None


def parse_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def parse_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        candidate = text[:10]
        try:
            return date.fromisoformat(candidate).isoformat()
        except ValueError:
            return None


def normalize(record: Any) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None

    row = {field: pick(record, keys) for field, keys in FIELD_CANDIDATES.items()}
    normalized_date = parse_date(row["date"])
    close = parse_number(row["close"])
    if normalized_date is None or close is None:
        return None

    return {
        "date": normalized_date,
        "open": parse_number(row["open"]),
        "high": parse_number(row["high"]),
        "low": parse_number(row["low"]),
        "close": close,
        "volume": parse_number(row["volume"]),
    }


def load_existing() -> list[dict[str, Any]]:
    if not DATA_PATH.exists() or DATA_PATH.stat().st_size == 0:
        return []
    try:
        payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read {DATA_PATH}: {exc}") from exc
    if not isinstance(payload, list):
        raise RuntimeError(f"Expected {DATA_PATH} to contain a JSON array")
    return [row for row in (normalize(item) for item in payload) if row]


def records_from_response(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, dict):
        for key in ("content", "data", "results", "items"):
            value = response.get(key)
            if isinstance(value, list):
                return value
        return []
    return response if isinstance(response, list) else []


def fetch_history(client: NepseScraper, start_date: str, end_date: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    page = 0
    while True:
        response = client.get_ticker_price_history(
            TICKER,
            start_date,
            end_date,
            page=page,
            size=PAGE_SIZE,
        )
        page_records = records_from_response(response)
        records.extend(page_records)
        print(f"Fetched page {page + 1}: {len(page_records)} record(s).")

        if not isinstance(response, dict):
            break
        total_pages = response.get("totalPages")
        if response.get("last") is True or not page_records:
            break
        if isinstance(total_pages, int) and page + 1 >= total_pages:
            break
        page += 1
    return records


def write_json(rows: list[dict[str, Any]]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="sjcl-", suffix=".json", dir=DATA_PATH.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_name, DATA_PATH)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    try:
        existing = load_existing()
        by_date = {row["date"]: row for row in existing}
        last_date = max(by_date) if by_date else None
        start_date = (
            date.fromisoformat(last_date) + timedelta(days=1)
        ).isoformat() if last_date else BACKFILL_START
        end_date = os.getenv("SJCL_END_DATE", date.today().isoformat())

        if start_date > end_date:
            print(f"Already up to date through {last_date}. Nothing to fetch.")
            return 0

        verify_ssl = os.getenv("NEPSE_VERIFY_SSL", "false").lower() in {"1", "true", "yes"}
        print(f"Fetching {TICKER} history from {start_date} to {end_date}...")
        client = NepseScraper(verify_ssl=verify_ssl)
        raw_records = fetch_history(client, start_date, end_date)
        normalized = [row for row in (normalize(item) for item in raw_records) if row]

        if not normalized:
            message = "NEPSE returned no valid SJCL records. Existing data was preserved."
            print(message)
            return 1 if not existing else 0

        for row in normalized:
            by_date[row["date"]] = row
        merged = sorted(by_date.values(), key=lambda row: row["date"])
        write_json(merged)
        print(
            f"Saved {len(normalized)} fetched record(s); "
            f"total history is now {len(merged)} trading day(s), "
            f"latest {merged[-1]['date']}."
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - CI should preserve existing data
        print(f"Fetch failed: {exc}", file=sys.stderr)
        print("Existing data was left untouched.", file=sys.stderr)
        return 0 if DATA_PATH.exists() and DATA_PATH.stat().st_size > 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
