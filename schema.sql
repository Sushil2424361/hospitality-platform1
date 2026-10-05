-- Hospitality Management Platform - database schema (SQLite)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS menu_categories (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE,
    sort_order    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS menu_items (
    item_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id        INTEGER NOT NULL REFERENCES menu_categories(category_id),
    item_name          TEXT NOT NULL,
    description        TEXT DEFAULT '',
    price              REAL NOT NULL CHECK (price >= 0),
    cost               REAL NOT NULL CHECK (cost >= 0),
    is_house_specialty INTEGER NOT NULL DEFAULT 0,
    is_available       INTEGER NOT NULL DEFAULT 1,
    is_active          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS dining_tables (
    table_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    table_label TEXT NOT NULL UNIQUE,
    seats       INTEGER NOT NULL CHECK (seats > 0)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    phone         TEXT NOT NULL UNIQUE,
    email         TEXT,
    dietary_notes TEXT DEFAULT '',
    consent_given INTEGER NOT NULL DEFAULT 0,
    consent_date  TEXT,
    is_anonymised INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customer_notes (
    note_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    author_role TEXT NOT NULL,
    note_text   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id     INTEGER NOT NULL REFERENCES dining_tables(table_id),
    customer_id  INTEGER REFERENCES customers(customer_id),  -- NULL = walk-in
    status       TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed','voided')),
    opened_at    TEXT NOT NULL,
    closed_at    TEXT,
    total_amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id),
    item_id       INTEGER NOT NULL REFERENCES menu_items(item_id),
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    REAL NOT NULL,  -- frozen at time of sale
    unit_cost     REAL NOT NULL,  -- frozen at time of sale
    item_note     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS daily_item_sales (
    summary_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_date     TEXT NOT NULL,
    item_id       INTEGER NOT NULL REFERENCES menu_items(item_id),
    quantity_sold INTEGER NOT NULL DEFAULT 0,
    revenue       REAL NOT NULL DEFAULT 0,
    total_cost    REAL NOT NULL DEFAULT 0,
    UNIQUE (sale_date, item_id)
);

CREATE TABLE IF NOT EXISTS special_suggestions (
    suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    for_date      TEXT NOT NULL,
    item_id       INTEGER NOT NULL REFERENCES menu_items(item_id),
    score         REAL,
    reason_text   TEXT DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'suggested'
                  CHECK (status IN ('suggested','approved','rejected')),
    generated_at  TEXT NOT NULL,
    UNIQUE (for_date, item_id)
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_opened ON orders(opened_at);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);