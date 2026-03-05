import argparse
import csv
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from seed.mock_data import NGOS, RESTAURANTS
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from seed.mock_data import NGOS, RESTAURANTS


def write_restaurants_csv(output_dir: Path) -> Path:
    output_path = output_dir / "restaurants.csv"
    headers = [
        "id",
        "name",
        "address",
        "latitude",
        "longitude",
        "cuisine_type",
        "avg_daily_covers",
        "reliability_score",
        "trust_rating",
        "created_at",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for restaurant in RESTAURANTS:
            writer.writerow(
                {
                    "id": restaurant["id"],
                    "name": restaurant["name"],
                    "address": restaurant["address"],
                    "latitude": restaurant["latitude"],
                    "longitude": restaurant["longitude"],
                    "cuisine_type": restaurant.get("cuisine_type", ""),
                    "avg_daily_covers": restaurant.get("avg_daily_covers", 50),
                    "reliability_score": restaurant.get("reliability_score", 0.8),
                    "trust_rating": round(random.uniform(3.0, 5.0), 1),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    return output_path


def write_ngos_csv(output_dir: Path) -> Path:
    output_path = output_dir / "ngos.csv"
    headers = [
        "id",
        "name",
        "address",
        "latitude",
        "longitude",
        "capacity",
        "current_load",
        "urgency_score",
        "reliability_score",
        "phone",
        "created_at",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for ngo in NGOS:
            writer.writerow(
                {
                    "id": ngo["id"],
                    "name": ngo["name"],
                    "address": ngo["address"],
                    "latitude": ngo["latitude"],
                    "longitude": ngo["longitude"],
                    "capacity": ngo.get("capacity", 100),
                    "current_load": ngo.get("current_load", 0),
                    "urgency_score": ngo.get("urgency_score", 0.5),
                    "reliability_score": ngo.get("reliability_score", 0.8),
                    "phone": ngo.get("phone", ""),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    return output_path


def write_donations_csv(output_dir: Path, count: int, allow_null_ngo: bool) -> Path:
    output_path = output_dir / "donations.csv"
    headers = [
        "restaurant_id",
        "ngo_id",
        "food_quantity",
        "food_type",
        "pickup_time",
        "status",
        "notes",
        "created_at",
    ]

    restaurant_ids = [restaurant["id"] for restaurant in RESTAURANTS]
    ngo_ids = [ngo["id"] for ngo in NGOS]
    status_values = ["pending", "matched", "accepted", "picked_up", "delivered"]
    status_weights = [0.25, 0.2, 0.2, 0.15, 0.2]
    food_types = ["mixed", "rice", "bread", "meals", "snacks"]

    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for _ in range(count):
            restaurant_id = random.choice(restaurant_ids)
            ngo_id = random.choice(ngo_ids)
            if allow_null_ngo and random.random() < 0.35:
                ngo_id = None

            status = random.choices(status_values, weights=status_weights, k=1)[0]
            if ngo_id is None and status != "pending":
                status = "pending"

            created_at = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 120), hours=random.randint(0, 23))
            pickup_time = ""
            if status in ("matched", "accepted", "picked_up", "delivered"):
                pickup_time = (created_at + timedelta(hours=random.randint(1, 12))).isoformat()

            writer.writerow(
                {
                    "restaurant_id": restaurant_id,
                    "ngo_id": "" if ngo_id is None else ngo_id,
                    "food_quantity": random.randint(5, 120),
                    "food_type": random.choice(food_types),
                    "pickup_time": pickup_time,
                    "status": status,
                    "notes": "synthetic donation seed",
                    "created_at": created_at.isoformat(),
                }
            )

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate CSV seed files for Supabase import")
    parser.add_argument("--donation-count", type=int, default=1000, help="Number of synthetic donation rows")
    parser.add_argument("--allow-null-ngo", action="store_true", help="Allow blank ngo_id rows in donations CSV")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible output")
    parser.add_argument("--output-dir", default="seed/csv", help="Output directory for CSV files")
    args = parser.parse_args()

    random.seed(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    restaurants_csv = write_restaurants_csv(output_dir)
    ngos_csv = write_ngos_csv(output_dir)
    donations_csv = write_donations_csv(output_dir, args.donation_count, args.allow_null_ngo)

    print(f"Generated: {restaurants_csv.resolve()}")
    print(f"Generated: {ngos_csv.resolve()}")
    print(f"Generated: {donations_csv.resolve()} ({args.donation_count} rows)")
    print("Import order in Supabase: restaurants -> ngos -> donations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
