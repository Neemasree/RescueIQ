import argparse
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import delete, func, select, text

load_dotenv()

from ml import predictor
from models import Donation, NGO, Prediction, Restaurant, SessionLocal, init_db
from seed.mock_data import DONATIONS, NGOS, RESTAURANTS


def generate_mock_historical_data(count: int, seed_value: int = 42) -> list[dict]:
    random.seed(seed_value)
    records: list[dict] = []
    start_date = date.today() - timedelta(days=120)

    restaurant_index = {restaurant["id"]: restaurant for restaurant in RESTAURANTS}
    restaurant_ids = list(restaurant_index.keys())

    for index in range(count):
        restaurant_id = random.choice(restaurant_ids)
        restaurant = restaurant_index[restaurant_id]

        day_of_week = random.randint(0, 6)
        event_probability = 0.65 if day_of_week in (4, 5) else 0.1
        event_flag = 1 if random.random() < event_probability else 0
        weather_score = round(random.uniform(0.3, 1.0), 2)

        baseline = restaurant["avg_daily_covers"] * 0.2
        surplus_core = baseline + (8 * event_flag) + (5 * weather_score)
        past_surplus = round(max(0.0, surplus_core + random.gauss(0, 3)), 1)
        actual_surplus = round(max(0.0, past_surplus + random.gauss(0, 1.2)), 1)

        prediction_date = (start_date + timedelta(days=index % 120)).isoformat()

        records.append(
            {
                "restaurant_id": restaurant_id,
                "day_of_week": day_of_week,
                "event_flag": event_flag,
                "weather_score": weather_score,
                "past_surplus": past_surplus,
                "avg_daily_covers": restaurant["avg_daily_covers"],
                "actual_surplus": actual_surplus,
                "prediction_date": prediction_date,
            }
        )

    return records


def upsert_restaurants(session) -> None:
    for item in RESTAURANTS:
        restaurant = session.get(Restaurant, item["id"])
        if restaurant is None:
            restaurant = Restaurant(id=item["id"])
            session.add(restaurant)
        restaurant.name = item["name"]
        restaurant.address = item["address"]
        restaurant.latitude = item["latitude"]
        restaurant.longitude = item["longitude"]
        restaurant.cuisine_type = item.get("cuisine_type")
        restaurant.avg_daily_covers = item["avg_daily_covers"]
        restaurant.reliability_score = item.get("reliability_score", 0.8)


def upsert_ngos(session) -> None:
    for item in NGOS:
        ngo = session.get(NGO, item["id"])
        if ngo is None:
            ngo = NGO(id=item["id"])
            session.add(ngo)
        ngo.name = item["name"]
        ngo.address = item["address"]
        ngo.latitude = item["latitude"]
        ngo.longitude = item["longitude"]
        ngo.capacity = item.get("capacity", 100)
        ngo.current_load = item.get("current_load", 0)
        ngo.urgency_score = item.get("urgency_score", 0.5)
        ngo.reliability_score = item.get("reliability_score", 0.8)
        ngo.phone = item.get("phone")


def reseed_donations(session) -> None:
    session.execute(text("DELETE FROM donations"))
    for item in DONATIONS:
        session.execute(
            text(
                """
                INSERT INTO donations (id, restaurant_id, ngo_id, food_quantity, food_type, pickup_time, status, notes, created_at)
                VALUES (:id, :restaurant_id, :ngo_id, :food_quantity, :food_type, :pickup_time, :status, :notes, :created_at)
                """
            ),
            {
                "id": item["id"],
                "restaurant_id": item["restaurant_id"],
                "ngo_id": item.get("ngo_id"),
                "food_quantity": item["food_quantity"],
                "food_type": item.get("food_type", "mixed"),
                "pickup_time": None,
                "status": item.get("status", "pending").lower(),
                "notes": None,
                "created_at": datetime.fromisoformat(item["created_at"]),
            },
        )


def reseed_predictions(session, historical_data: list[dict]) -> None:
    session.execute(delete(Prediction))

    for row in historical_data:
        prediction = Prediction(
            restaurant_id=row["restaurant_id"],
            predicted_surplus=row["past_surplus"],
            prediction_date=date.fromisoformat(row["prediction_date"]),
            day_of_week=row["day_of_week"],
            event_flag=row["event_flag"],
            weather_score=row["weather_score"],
            actual_surplus=row["actual_surplus"],
        )
        session.add(prediction)


def sync_postgres_sequences(session) -> None:
    session.execute(text("SELECT setval(pg_get_serial_sequence('restaurants','id'), COALESCE((SELECT MAX(id) FROM restaurants),1));"))
    session.execute(text("SELECT setval(pg_get_serial_sequence('ngos','id'), COALESCE((SELECT MAX(id) FROM ngos),1));"))
    session.execute(text("SELECT setval(pg_get_serial_sequence('donations','id'), COALESCE((SELECT MAX(id) FROM donations),1));"))
    session.execute(text("SELECT setval(pg_get_serial_sequence('predictions','id'), COALESCE((SELECT MAX(id) FROM predictions),1));"))


def ensure_schema_compatibility(session) -> None:
    statements = [
        "ALTER TABLE IF EXISTS restaurants ADD COLUMN IF NOT EXISTS name TEXT;",
        "ALTER TABLE IF EXISTS restaurants ADD COLUMN IF NOT EXISTS address TEXT;",
        "ALTER TABLE IF EXISTS restaurants ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;",
        "ALTER TABLE IF EXISTS restaurants ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;",
        "ALTER TABLE IF EXISTS restaurants ADD COLUMN IF NOT EXISTS cuisine_type TEXT;",
        "ALTER TABLE IF EXISTS restaurants ADD COLUMN IF NOT EXISTS avg_daily_covers INTEGER DEFAULT 50;",
        "ALTER TABLE IF EXISTS restaurants ADD COLUMN IF NOT EXISTS reliability_score DOUBLE PRECISION DEFAULT 0.8;",
        "ALTER TABLE IF EXISTS restaurants ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();",
        "ALTER TABLE IF EXISTS restaurants ADD COLUMN IF NOT EXISTS user_id VARCHAR(36);",

        "ALTER TABLE IF EXISTS ngos ADD COLUMN IF NOT EXISTS name TEXT;",
        "ALTER TABLE IF EXISTS ngos ADD COLUMN IF NOT EXISTS address TEXT;",
        "ALTER TABLE IF EXISTS ngos ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;",
        "ALTER TABLE IF EXISTS ngos ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;",
        "ALTER TABLE IF EXISTS ngos ADD COLUMN IF NOT EXISTS capacity INTEGER DEFAULT 100;",
        "ALTER TABLE IF EXISTS ngos ADD COLUMN IF NOT EXISTS current_load INTEGER DEFAULT 0;",
        "ALTER TABLE IF EXISTS ngos ADD COLUMN IF NOT EXISTS urgency_score DOUBLE PRECISION DEFAULT 0.5;",
        "ALTER TABLE IF EXISTS ngos ADD COLUMN IF NOT EXISTS reliability_score DOUBLE PRECISION DEFAULT 0.8;",
        "ALTER TABLE IF EXISTS ngos ADD COLUMN IF NOT EXISTS phone TEXT;",
        "ALTER TABLE IF EXISTS ngos ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();",
        "ALTER TABLE IF EXISTS ngos ADD COLUMN IF NOT EXISTS user_id VARCHAR(36);",

        "ALTER TABLE IF EXISTS donations ADD COLUMN IF NOT EXISTS restaurant_id INTEGER;",
        "ALTER TABLE IF EXISTS donations ADD COLUMN IF NOT EXISTS ngo_id INTEGER;",
        "ALTER TABLE IF EXISTS donations ADD COLUMN IF NOT EXISTS food_quantity INTEGER;",
        "ALTER TABLE IF EXISTS donations ADD COLUMN IF NOT EXISTS food_type TEXT DEFAULT 'mixed';",
        "ALTER TABLE IF EXISTS donations ADD COLUMN IF NOT EXISTS pickup_time TIMESTAMPTZ;",
        "ALTER TABLE IF EXISTS donations ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';",
        "ALTER TABLE IF EXISTS donations ADD COLUMN IF NOT EXISTS notes TEXT;",
        "ALTER TABLE IF EXISTS donations ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();",

        "ALTER TABLE IF EXISTS predictions ADD COLUMN IF NOT EXISTS restaurant_id INTEGER;",
        "ALTER TABLE IF EXISTS predictions ADD COLUMN IF NOT EXISTS predicted_surplus DOUBLE PRECISION;",
        "ALTER TABLE IF EXISTS predictions ADD COLUMN IF NOT EXISTS prediction_date DATE DEFAULT CURRENT_DATE;",
        "ALTER TABLE IF EXISTS predictions ADD COLUMN IF NOT EXISTS day_of_week INTEGER;",
        "ALTER TABLE IF EXISTS predictions ADD COLUMN IF NOT EXISTS event_flag INTEGER DEFAULT 0;",
        "ALTER TABLE IF EXISTS predictions ADD COLUMN IF NOT EXISTS weather_score DOUBLE PRECISION DEFAULT 0.5;",
        "ALTER TABLE IF EXISTS predictions ADD COLUMN IF NOT EXISTS actual_surplus DOUBLE PRECISION;",
        "ALTER TABLE IF EXISTS predictions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();",

        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS password_hash TEXT;",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS phone TEXT;",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
    ]
    for sql in statements:
        session.execute(text(sql))


def train_model_on_generated_data(historical_data: list[dict]) -> None:
    predictor.HISTORICAL_DATA = historical_data
    predictor._model = None
    predictor.get_model()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate mock dataset, seed Supabase, and train model.")
    parser.add_argument("--count", type=int, default=2000, help="Number of historical records to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic generation")
    parser.add_argument("--out", default="seed/generated_historical_data.json", help="Where to save generated dataset")
    args = parser.parse_args()

    init_db()

    historical_data = generate_mock_historical_data(args.count, args.seed)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(historical_data, indent=2), encoding="utf-8")

    session = SessionLocal()
    try:
        ensure_schema_compatibility(session)
        upsert_restaurants(session)
        upsert_ngos(session)
        session.flush()
        reseed_donations(session)
        reseed_predictions(session, historical_data)
        sync_postgres_sequences(session)
        session.commit()

        restaurant_count = session.scalar(select(func.count()).select_from(Restaurant))
        ngo_count = session.scalar(select(func.count()).select_from(NGO))
        donation_count = session.scalar(select(func.count()).select_from(Donation))
        prediction_count = session.scalar(select(func.count()).select_from(Prediction))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"Saved generated dataset: {out_path.resolve()} ({len(historical_data)} rows)")
    print(
        "Supabase seeded counts -> "
        f"restaurants={restaurant_count}, ngos={ngo_count}, donations={donation_count}, predictions={prediction_count}"
    )

    train_model_on_generated_data(historical_data)
    print("Model training completed using generated dataset.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
