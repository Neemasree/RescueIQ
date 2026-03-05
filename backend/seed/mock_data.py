import os
import json
import random
from datetime import datetime, timedelta

# ── Mock data for seeding the local JSON-based mock DB ───────────────────────
# When Supabase is not configured, the app uses this in-memory store.

RESTAURANTS = [
    {"id": 1, "name": "Spice Garden", "address": "12 MG Road, Bangalore", "latitude": 12.9716, "longitude": 77.5946, "cuisine_type": "Indian", "avg_daily_covers": 80, "reliability_score": 0.9},
    {"id": 2, "name": "Green Leaf Bistro", "address": "45 Koramangala, Bangalore", "latitude": 12.9352, "longitude": 77.6245, "cuisine_type": "Continental", "avg_daily_covers": 60, "reliability_score": 0.85},
    {"id": 3, "name": "The Curry House", "address": "7 Indiranagar, Bangalore", "latitude": 12.9784, "longitude": 77.6408, "cuisine_type": "Indian", "avg_daily_covers": 100, "reliability_score": 0.75},
    {"id": 4, "name": "Pizza Paradiso", "address": "21 Whitefield, Bangalore", "latitude": 12.9698, "longitude": 77.7499, "cuisine_type": "Italian", "avg_daily_covers": 70, "reliability_score": 0.8},
    {"id": 5, "name": "Dosa Delight", "address": "3 Jayanagar, Bangalore", "latitude": 12.9308, "longitude": 77.5838, "cuisine_type": "South Indian", "avg_daily_covers": 120, "reliability_score": 0.95},
]

NGOS = [
    {"id": 1, "name": "Akshaya Patra", "address": "Rajajinagar, Bangalore", "latitude": 13.0067, "longitude": 77.5525, "capacity": 500, "current_load": 120, "urgency_score": 0.9, "reliability_score": 0.95, "phone": "+91-80-2328-0001"},
    {"id": 2, "name": "Robin Hood Army", "address": "Koramangala, Bangalore", "latitude": 12.9279, "longitude": 77.6271, "capacity": 200, "current_load": 80, "urgency_score": 0.75, "reliability_score": 0.88, "phone": "+91-99001-12345"},
    {"id": 3, "name": "Feeding India", "address": "BTM Layout, Bangalore", "latitude": 12.9166, "longitude": 77.6101, "capacity": 300, "current_load": 200, "urgency_score": 0.85, "reliability_score": 0.9, "phone": "+91-80-4567-8901"},
    {"id": 4, "name": "No Food Waste", "address": "HSR Layout, Bangalore", "latitude": 12.9116, "longitude": 77.6389, "capacity": 150, "current_load": 30, "urgency_score": 0.6, "reliability_score": 0.8, "phone": "+91-98765-43210"},
    {"id": 5, "name": "Smile Foundation", "address": "Marathahalli, Bangalore", "latitude": 12.9591, "longitude": 77.6972, "capacity": 250, "current_load": 100, "urgency_score": 0.7, "reliability_score": 0.85, "phone": "+91-80-1234-5678"},
]

# Historical surplus records (for XGBoost training)
def generate_historical_data():
    records = []
    start = datetime.now() - timedelta(days=90)
    for day_offset in range(90):
        date = start + timedelta(days=day_offset)
        day_of_week = date.weekday()
        for restaurant in RESTAURANTS:
            base = restaurant["avg_daily_covers"] * 0.2
            event_flag = 1 if day_of_week in [4, 5] else 0  # Fri/Sat busier
            weather_score = round(random.uniform(0.3, 1.0), 2)
            noise = random.gauss(0, 3)
            surplus = max(0, base + event_flag * 8 + weather_score * 5 + noise)
            records.append({
                "restaurant_id": restaurant["id"],
                "day_of_week": day_of_week,
                "event_flag": event_flag,
                "weather_score": weather_score,
                "past_surplus": round(surplus, 1),
                "avg_daily_covers": restaurant["avg_daily_covers"],
                "actual_surplus": round(surplus + random.gauss(0, 1), 1),
            })
    return records

HISTORICAL_DATA = generate_historical_data()

DONATIONS = [
    {"id": 1, "restaurant_id": 1, "ngo_id": 2, "food_quantity": 25, "food_type": "Rice & Curry", "status": "delivered", "created_at": (datetime.now() - timedelta(days=3)).isoformat()},
    {"id": 2, "restaurant_id": 3, "ngo_id": 1, "food_quantity": 40, "food_type": "Mixed Meals", "status": "delivered", "created_at": (datetime.now() - timedelta(days=2)).isoformat()},
    {"id": 3, "restaurant_id": 5, "ngo_id": 3, "food_quantity": 55, "food_type": "Idli & Dosa", "status": "picked_up", "created_at": (datetime.now() - timedelta(days=1)).isoformat()},
    {"id": 4, "restaurant_id": 2, "ngo_id": 4, "food_quantity": 18, "food_type": "Sandwiches", "status": "accepted", "created_at": datetime.now().isoformat()},
]

IMPACT = {
    "meals_rescued": 138,
    "food_waste_prevented_kg": 46,
    "co2_reduced_kg": 75,
    "ngos_supported": 4,
    "restaurants_participating": 5,
    "donations_this_week": 4,
}
