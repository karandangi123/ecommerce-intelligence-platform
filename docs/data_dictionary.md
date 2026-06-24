# Data Dictionary
*Schema Reference and Column Definitions for Olist Star Schema*

---

## 1. Dimension Tables

### `dim_customers`
Contains unique customer records, mapped to their primary location.
* **`customer_unique_id`** (`VARCHAR(50)`, Primary Key): Persistent identifier for a unique customer across all orders.
* **`zip_code_prefix`** (`VARCHAR(10)`): First 5 digits of customer zip code.
* **`city`** (`VARCHAR(100)`): Customer city name (cleaned and formatted).
* **`state`** (`CHAR(2)`): Customer state code (e.g. "SP", "RJ").

### `dim_sellers`
Contains unique merchant records.
* **`seller_id`** (`VARCHAR(50)`, Primary Key): Unique identifier for a seller.
* **`zip_code_prefix`** (`VARCHAR(10)`): Seller zip code prefix.
* **`city`** (`VARCHAR(100)`): Seller city name.
* **`state`** (`CHAR(2)`): Seller state code.

### `dim_products`
Contains catalog products with English category names and specifications.
* **`product_id`** (`VARCHAR(50)`, Primary Key): Unique product identifier.
* **`category_english`** (`VARCHAR(100)`): English product category (Portuguese categories mapped via translation table; missing values defaulted to `'unknown'`).
* **`weight_g`** (`INT`): Product weight in grams.
* **`length_cm`** (`INT`): Product length in centimeters.
* **`height_cm`** (`INT`): Product height in centimeters.
* **`width_cm`** (`INT`): Product width in centimeters.

---

## 2. Fact Tables

### `fact_orders`
The central transaction fact table.
* **`order_id`** (`VARCHAR(50)`, Primary Key): Unique identifier for an order transaction.
* **`customer_unique_id`** (`VARCHAR(50)`, Foreign Key ➔ `dim_customers`): Customer who placed the order.
* **`order_status`** (`VARCHAR(20)`): State of the order (e.g., "delivered", "shipped", "canceled").
* **`purchase_timestamp`** (`TIMESTAMP`): Time order was placed.
* **`approved_timestamp`** (`TIMESTAMP`): Time payment was approved.
* **`delivered_carrier_timestamp`** (`TIMESTAMP`): Time carrier picked up the package.
* **`delivered_customer_timestamp`** (`TIMESTAMP`): Time package arrived at customer's home.
* **`estimated_delivery_timestamp`** (`TIMESTAMP`): Estimated delivery date promised at checkout.
* **`total_price`** (`NUMERIC(10,2)`): Total item prices in the order.
* **`total_freight`** (`NUMERIC(10,2)`): Total shipping cost.
* **`total_payment`** (`NUMERIC(10,2)`): Total amount paid (price + freight).

### `fact_deliveries`
The logistics fact table. One record per unique Order-Seller combination.
* **`order_id`** (`VARCHAR(50)`, Composite Primary Key): Order identifier.
* **`seller_id`** (`VARCHAR(50)`, Composite Primary Key, Foreign Key ➔ `dim_sellers`): Merchant shipping the package.
* **`customer_unique_id`** (`VARCHAR(50)`, Foreign Key ➔ `dim_customers`): Recipient.
* **`purchase_timestamp`** (`TIMESTAMP`): Order purchase date.
* **`delivered_customer_timestamp`** (`TIMESTAMP`): Actual delivery date.
* **`estimated_delivery_timestamp`** (`TIMESTAMP`): Promised delivery date.
* **`actual_delivery_days`** (`NUMERIC(5,2)`): Total days from purchase to delivery.
* **`estimated_delivery_days`** (`NUMERIC(5,2)`): Total days promised for shipping.
* **`days_difference`** (`NUMERIC(5,2)`): Actual days minus Estimated days (positive if late, negative if early).
* **`is_late`** (`INT`): Binary flag (`1` if package arrived late, `0` if on-time or early).
