import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


PROMPT_TEMPLATE = """You are generating synthetic tabular data for food surplus prediction.
Return ONLY valid JSON (no markdown, no explanation).
Output format must be a JSON object with one key: rows.
rows must be a JSON array of objects.
Generate exactly {record_count} records.
Each record must have these keys in this exact order:
restaurant_id (int, one of: 1,2,3,4,5)
day_of_week (int, 0-6; 0=Monday)
event_flag (int, 0 or 1)
weather_score (float, 0.30 to 1.00, 2 decimals)
past_surplus (float, >=0, 1 decimal)
avg_daily_covers (int, based on restaurant_id mapping below)
actual_surplus (float, >=0, 1 decimal)
Restaurant mapping:
1 -> avg_daily_covers 80
2 -> avg_daily_covers 60
3 -> avg_daily_covers 100
4 -> avg_daily_covers 70
5 -> avg_daily_covers 120
Data realism rules:
event_flag should be 1 mostly on Friday/Saturday (day_of_week 4 or 5), rarely otherwise.
Higher avg_daily_covers should generally increase surplus.
Higher weather_score should slightly increase surplus.
actual_surplus should be close to past_surplus with small random noise.
Keep most actual_surplus in range 5-45, with occasional values up to 70.
Never output negative values.
Ensure good distribution across all 5 restaurants and all 7 weekdays.
Final output must be strictly valid JSON.
Example top-level shape:
{{
    "rows": [
        {{"restaurant_id": 1, "day_of_week": 0, "event_flag": 0, "weather_score": 0.67, "past_surplus": 14.2, "avg_daily_covers": 80, "actual_surplus": 15.1}}
    ]
}}
"""

REQUIRED_KEYS = [
    "restaurant_id",
    "day_of_week",
    "event_flag",
    "weather_score",
    "past_surplus",
    "avg_daily_covers",
    "actual_surplus",
]


def _extract_json_array(text: str) -> list:
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and isinstance(parsed.get("rows"), list):
            return parsed["rows"]
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON array found in Ollama output")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, list):
        raise ValueError("Extracted JSON is not an array")
    return parsed


def _repair_json_text(text: str) -> str:
    repaired = text
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    repaired = repaired.strip()
    return repaired


def _validate_rows(rows: list) -> None:
    if not isinstance(rows, list):
        raise ValueError("Output is not a JSON array")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Row {index} is not an object")


def _normalize_rows(rows: list) -> list:
    normalized = []
    for index, row in enumerate(rows):
        missing = [key for key in REQUIRED_KEYS if key not in row]
        if missing:
            raise ValueError(f"Row {index} missing keys: {missing}")

        clean = {
            "restaurant_id": int(row["restaurant_id"]),
            "day_of_week": int(row["day_of_week"]),
            "event_flag": int(row["event_flag"]),
            "weather_score": round(float(row["weather_score"]), 2),
            "past_surplus": round(max(0.0, float(row["past_surplus"])), 1),
            "avg_daily_covers": int(row["avg_daily_covers"]),
            "actual_surplus": round(max(0.0, float(row["actual_surplus"])), 1),
        }
        normalized.append(clean)
    return normalized


def _generate(model: str, prompt: str, timeout_seconds: int) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.3},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url="http://localhost:11434/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            response_body = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to call local Ollama API: {exc}") from exc

    parsed = json.loads(response_body)
    if "response" not in parsed:
        raise RuntimeError("Ollama API response missing 'response' field")
    return str(parsed["response"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate food surplus mock data with local Ollama.")
    parser.add_argument("--model", default="llama3", help="Ollama model name (default: llama3)")
    parser.add_argument("--count", type=int, default=2000, help="Number of records to generate")
    parser.add_argument("--out", default="food_surplus_data.json", help="Output JSON file path")
    parser.add_argument("--batch-size", type=int, default=200, help="Rows to generate per Ollama call")
    parser.add_argument("--retries", type=int, default=3, help="Retry count when model returns invalid JSON")
    parser.add_argument("--timeout", type=int, default=1200, help="Ollama timeout in seconds")
    args = parser.parse_args()

    out_path = Path(args.out).resolve()

    last_error: Exception | None = None
    all_rows = []
    remaining = args.count
    batch_index = 0

    while remaining > 0:
        batch_index += 1
        batch_count = min(args.batch_size, remaining)
        prompt = PROMPT_TEMPLATE.format(record_count=batch_count)
        success = False

        for attempt in range(1, args.retries + 1):
            try:
                raw = _generate(args.model, prompt, args.timeout)
                raw = _repair_json_text(raw)
                data = _extract_json_array(raw)
                _validate_rows(data)
                data = _normalize_rows(data)
                if len(data) != batch_count:
                    raise ValueError(f"Expected {batch_count} rows but got {len(data)}")
                all_rows.extend(data)
                remaining -= batch_count
                print(f"Batch {batch_index}: +{batch_count} rows (total {len(all_rows)}/{args.count})")
                success = True
                break
            except Exception as exc:
                last_error = exc
                print(f"Batch {batch_index} attempt {attempt}/{args.retries} failed: {exc}")

        if not success:
            print(f"Generation failed at batch {batch_index}: {last_error}")
            return 1

    out_path.write_text(json.dumps(all_rows, indent=2), encoding="utf-8")
    print(f"Saved {len(all_rows)} records to {out_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
