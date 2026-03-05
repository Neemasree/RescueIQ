import argparse
import random
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

from models import NGO, Restaurant, SessionLocal, init_db
from seed.mock_data import NGOS, RESTAURANTS


def upsert_restaurants(session) -> None:
    for item in RESTAURANTS:
        row = session.get(Restaurant, item["id"])
        if row is None:
            row = Restaurant(id=item["id"])
            session.add(row)
        row.name = item["name"]
        row.address = item["address"]
        row.latitude = item["latitude"]
        row.longitude = item["longitude"]
        row.cuisine_type = item.get("cuisine_type")
        row.avg_daily_covers = item.get("avg_daily_covers", 50)
        row.reliability_score = item.get("reliability_score", 0.8)
        if hasattr(row, "trust_rating"):
            row.trust_rating = round(random.uniform(3.0, 5.0), 1)


def upsert_ngos(session) -> None:
    for item in NGOS:
        row = session.get(NGO, item["id"])
        if row is None:
            row = NGO(id=item["id"])
            session.add(row)
        row.name = item["name"]
        row.address = item["address"]
        row.latitude = item["latitude"]
        row.longitude = item["longitude"]
        row.capacity = item.get("capacity", 100)
        row.current_load = item.get("current_load", 0)
        row.urgency_score = item.get("urgency_score", 0.5)
        row.reliability_score = item.get("reliability_score", 0.8)
        row.phone = item.get("phone")


def is_ngo_nullable(session) -> bool:
    sql = text(
        """
        select is_nullable
        from information_schema.columns
        where table_schema='public' and table_name='donations' and column_name='ngo_id'
        """
    )
    value = session.execute(sql).scalar()
    return value == "YES"


def insert_synthetic_donations(session, count: int, truncate: bool) -> tuple[int, int]:
    if truncate:
        session.execute(text("DELETE FROM donations"))

    restaurant_ids = [item["id"] for item in RESTAURANTS]
    ngo_ids = [item["id"] for item in NGOS]
    ngo_nullable = is_ngo_nullable(session)

    status_values = ["pending", "matched", "accepted", "picked_up", "delivered"]
    weights = [0.25, 0.2, 0.2, 0.15, 0.2]

    rows = []
    total_food = 0
    for _ in range(count):
        restaurant_id = random.choice(restaurant_ids)
        ngo_id = random.choice(ngo_ids) if (not ngo_nullable or random.random() > 0.35) else None
        food_quantity = random.randint(5, 120)
        status = random.choices(status_values, weights=weights, k=1)[0]
        if ngo_id is None and status != "pending":
            status = "pending"

        created_at = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 120), hours=random.randint(0, 23))
        pickup_time = created_at + timedelta(hours=random.randint(1, 12)) if status in ("matched", "accepted", "picked_up", "delivered") else None

        rows.append(
            {
                "restaurant_id": restaurant_id,
                "ngo_id": ngo_id,
                "food_quantity": food_quantity,
                "food_type": random.choice(["mixed", "rice", "bread", "meals", "snacks"]),
                "pickup_time": pickup_time,
                "status": status,
                "notes": "synthetic donation seed",
                "created_at": created_at,
            }
        )
        total_food += food_quantity

    session.execute(
        text(
            """
            insert into donations (restaurant_id, ngo_id, food_quantity, food_type, pickup_time, status, notes, created_at)
            values (:restaurant_id, :ngo_id, :food_quantity, :food_type, :pickup_time, :status, :notes, :created_at)
            """
        ),
        rows,
    )

    return len(rows), total_food


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload restaurants and synthetic donation data to Supabase")
    parser.add_argument("--count", type=int, default=1000, help="Number of synthetic donations")
    parser.add_argument("--truncate", action="store_true", help="Delete existing donations before insert")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)
    init_db()

    session = SessionLocal()
    try:
        upsert_restaurants(session)
        upsert_ngos(session)
        session.flush()
        inserted, total_food = insert_synthetic_donations(session, args.count, args.truncate)
        session.commit()

        donation_count = session.execute(text("select count(*) from donations")).scalar()
        donated_food_total = session.execute(text("select coalesce(sum(food_quantity),0) from donations")).scalar()

        print(f"Inserted synthetic donations: {inserted}")
        print(f"Synthetic food quantity inserted: {total_food}")
        print(f"Donations table total rows: {donation_count}")
        print(f"Donations table total food_quantity: {donated_food_total}")
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
