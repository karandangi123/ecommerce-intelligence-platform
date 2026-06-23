CREATE TABLE IF NOT EXISTS dim_products (
    product_id INTEGER PRIMARY KEY,
    product_name VARCHAR NOT NULL,
    aisle_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL,
    unit_price DOUBLE NOT NULL,
    abc_class VARCHAR(1) -- A, B, or C
);
