CREATE TABLE IF NOT EXISTS fact_orders (
    order_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    aisle_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    add_to_cart_order INTEGER NOT NULL,
    reordered INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DOUBLE NOT NULL,
    subtotal DOUBLE NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
