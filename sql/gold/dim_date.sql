CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY, -- format: YYYYMMDD
    date DATE NOT NULL,
    day_of_week INTEGER NOT NULL, -- 0 (Sunday) to 6 (Saturday)
    day_name VARCHAR NOT NULL,
    hour_of_day INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL
);
