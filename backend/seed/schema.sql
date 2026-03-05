-- RescueIQ Database Schema
-- Run this in Supabase SQL editor

-- Enable PostGIS for geospatial queries (if available)
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- ─── Users ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('restaurant', 'ngo', 'admin')),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Restaurants ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS restaurants (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    cuisine_type TEXT,
    avg_daily_covers INT DEFAULT 50,
    reliability_score FLOAT DEFAULT 0.8,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── NGOs ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ngos (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    capacity INT DEFAULT 100,
    current_load INT DEFAULT 0,
    urgency_score FLOAT DEFAULT 0.5,
    reliability_score FLOAT DEFAULT 0.8,
    phone TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Donations ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS donations (
    id SERIAL PRIMARY KEY,
    restaurant_id INT REFERENCES restaurants(id),
    ngo_id INT REFERENCES ngos(id),
    food_quantity INT NOT NULL,
    food_type TEXT DEFAULT 'mixed',
    pickup_time TIMESTAMPTZ,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'matched', 'accepted', 'picked_up', 'delivered', 'cancelled')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Predictions ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    restaurant_id INT REFERENCES restaurants(id),
    predicted_surplus FLOAT NOT NULL,
    prediction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    day_of_week INT,
    event_flag INT DEFAULT 0,
    weather_score FLOAT DEFAULT 0.5,
    actual_surplus FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Pickup Logs ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pickup_logs (
    id SERIAL PRIMARY KEY,
    donation_id INT REFERENCES donations(id),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    driver_name TEXT,
    notes TEXT
);

-- ─── Impact Metrics ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS impact_metrics (
    id SERIAL PRIMARY KEY,
    donation_id INT REFERENCES donations(id) UNIQUE,
    meals_rescued INT NOT NULL DEFAULT 0,
    food_waste_prevented_kg FLOAT DEFAULT 0,
    co2_reduced_kg FLOAT DEFAULT 0,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);
