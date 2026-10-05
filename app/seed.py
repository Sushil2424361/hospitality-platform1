"""Seed the database with realistic demo data.

Run from the project folder:  python -m app.seed
Creates ~2,000 closed orders over the last 30 days with repeat guests.
"""
import random
from datetime import date, datetime, timedelta

from .db import get_conn, init_db
from . import scoring

random.seed(42)  # same demo data on every run

CATEGORIES = [("Starters", 1), ("Mains", 2), ("Desserts", 3), ("Drinks", 4)]

# (name, category, price, cost, is_house_specialty, is_available, description)
ITEMS = [
    ("Tomato Bruschetta",   "Starters", 6.50, 2.00, 0, 1, "Toasted bread, tomato, basil"),
    ("Garlic Prawns",       "Starters", 9.00, 3.80, 0, 1, "Prawns in garlic butter"),
    ("Soup of the Day",     "Starters", 5.50, 1.60, 0, 1, "Ask your waiter"),
    ("Caprese Salad",       "Starters", 7.00, 2.40, 0, 1, "Mozzarella, tomato, basil"),
    ("Calamari Rings",      "Starters", 8.50, 3.20, 0, 1, "With lemon aioli"),
    ("Stuffed Mushrooms",   "Starters", 7.50, 2.60, 0, 0, "Currently unavailable"),
    ("Margherita Pizza",    "Mains",   11.00, 3.50, 0, 1, "Tomato, mozzarella, basil"),
    ("Spaghetti Carbonara", "Mains",   13.50, 4.50, 1, 1, "House specialty - nonna's recipe"),
    ("Grilled Salmon",      "Mains",   18.00, 8.00, 0, 1, "With seasonal vegetables"),
    ("Ribeye Steak",        "Mains",   24.00, 12.00, 0, 1, "250g, cooked to order"),
    ("Chicken Parmesan",    "Mains",   15.00, 5.50, 0, 1, "With spaghetti"),
    ("Mushroom Risotto",    "Mains",   13.00, 4.20, 1, 1, "House specialty - porcini"),
    ("Lasagna al Forno",    "Mains",   14.00, 4.80, 1, 1, "House specialty - baked daily"),
    ("Vegetable Curry",     "Mains",   12.00, 3.80, 0, 1, "Vegan, with rice"),
    ("Fish and Chips",      "Mains",   14.50, 5.20, 0, 1, "Beer-battered haddock"),
    ("Beef Burger",         "Mains",   13.00, 4.60, 0, 0, "Currently unavailable"),
    ("Tiramisu",            "Desserts", 6.50, 2.10, 0, 1, "Classic Italian"),
    ("Chocolate Lava Cake", "Desserts", 7.00, 2.40, 0, 1, "Warm, with vanilla ice cream"),
    ("Panna Cotta",         "Desserts", 6.00, 1.80, 0, 1, "With berry coulis"),
    ("Ice Cream Sundae",    "Desserts", 5.50, 1.70, 0, 1, "Three scoops"),
    ("Cheesecake",          "Desserts", 6.50, 2.20, 0, 1, "New York style"),
    ("House Red Wine",      "Drinks",   6.00, 1.80, 0, 1, "By the glass"),
    ("Craft Beer",          "Drinks",   5.50, 1.60, 0, 1, "Local brewery"),
    ("Fresh Lemonade",      "Drinks",   4.00, 0.90, 0, 1, "Made daily"),
    ("Espresso",            "Drinks",   3.00, 0.60, 0, 1, ""),
]

FIRST = ["Anna", "Marco", "Sofia", "James", "Lucia", "Tom", "Elena", "Raj", "Mia",
         "Liam", "Olivia", "Noah", "Emma", "Lucas", "Grace", "Henry", "Chloe",
         "Diego", "Yuki", "Priya"]
LAST = ["Rossi", "Smith", "Kim", "Garcia", "Muller", "Brown", "Silva", "Patel",
        "Chen", "Jones", "Bianchi", "Taylor", "Costa", "Nguyen", "Khan", "Moretti",
        "Evans", "Santos", "Tanaka", "Sharma"]

DIETARY = ["Allergic to peanuts", "Vegetarian", "Gluten-free", "Lactose intolerant",
           "Allergic to shellfish", "Vegan", "No pork", "Allergic to tree nuts",
           "Low sodium", "No dairy", "Diabetic - low sugar", "Allergic to eggs",
           "Halal", "No spicy food", "Allergic to sesame"]

STAFF_NOTES = ["Prefers a quiet corner table.", "Likes sparkling water on arrival.",
               "Birthday regular - offer a dessert candle.", "Always tips well, very friendly.",
               "Double-check allergy with the kitchen.", "Often brings business clients.",
               "Prefers a window seat.", "Ask about their dog, Milo."]

TABLES = [("T1", 2), ("T2", 2), ("T3", 4), ("T4", 4),
          ("T5", 6), ("T6", 4), ("T7", 8), ("T8", 2)]

# how popular each item is (a few clear favourites so rankings look convincing)
POPULARITY = {"Margherita Pizza": 9, "Tiramisu": 7, "House Red Wine": 8,
              "Ribeye Steak": 5, "Chicken Parmesan": 5, "Espresso": 6,
              "Craft Beer": 5, "Fresh Lemonade": 4, "Caprese Salad": 2,
              "Soup of the Day": 2, "Vegetable Curry": 2, "Panna Cotta": 3,
              "Grilled Salmon": 3, "Fish and Chips": 4, "Ice Cream Sundae": 3,
              "Chocolate Lava Cake": 4, "Garlic Prawns": 3, "Calamari Rings": 2,
              "Tomato Bruschetta": 3, "Cheesecake": 2}


def run():
    init_db()
    with get_conn() as conn:
        if conn.execute("SELECT COUNT(*) AS c FROM menu_items").fetchone()["c"]:
            print("Database already has data. Delete restaurant.db and run again to reseed.")
            return

        # --- menu ---
        cat_id = {}
        for name, sort in CATEGORIES:
            cur = conn.execute(
                "INSERT INTO menu_categories (category_name, sort_order) VALUES (?, ?)",
                (name, sort))
            cat_id[name] = cur.lastrowid
        item_id = {}
        for name, cat, price, cost, hs, avail, desc in ITEMS:
            cur = conn.execute("""
                INSERT INTO menu_items (category_id, item_name, description, price, cost,
                                        is_house_specialty, is_available, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (cat_id[cat], name, desc, price, cost, hs, avail))
            item_id[name] = cur.lastrowid
        for label, seats in TABLES:
            conn.execute("INSERT INTO dining_tables (table_label, seats) VALUES (?, ?)",
                         (label, seats))

        # --- guests (all consented; about 15 with dietary notes) ---
        guest_ids = []
        favourites = {}  # guest -> their favourite item ids
        sellable = [item_id[n] for n, c, p, co, hs, av, d in ITEMS if av == 1]
        names = [f"{f} {l}" for l in LAST[:2] for f in FIRST]  # 40 unique names
        for i in range(40):
            full_name = names[i]
            dietary = DIETARY[i] if i < 15 else ""
            created = (date.today() - timedelta(days=random.randint(40, 400))).isoformat()
            cur = conn.execute("""
                INSERT INTO customers (full_name, phone, email, dietary_notes,
                                       consent_given, consent_date, created_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
            """, (full_name, f"555-01{10 + i}",
                  full_name.lower().replace(" ", ".") + "@example.com",
                  dietary, created, created))
            guest_ids.append(cur.lastrowid)
            favourites[cur.lastrowid] = random.sample(sellable, 2)

        # a few staff notes on random guests
        for _ in range(12):
            conn.execute("""
                INSERT INTO customer_notes (customer_id, author_role, note_text, created_at)
                VALUES (?, ?, ?, ?)
            """, (random.choice(guest_ids), random.choice(["Waiter", "Manager"]),
                  random.choice(STAFF_NOTES),
                  (date.today() - timedelta(days=random.randint(1, 20))).isoformat() + " 19:00:00"))

        # --- ~2,000 closed orders over the last 30 days (weekends busier) ---
        today = date.today()
        days = [today - timedelta(days=i) for i in range(29, -1, -1)]
        weights = [1.6 if d.weekday() in (4, 5) else 1.3 if d.weekday() == 6 else 1.0
                   for d in days]
        wsum = sum(weights)
        counts = [round(2000 * w / wsum) for w in weights]
        counts[0] += 2000 - sum(counts)  # fix rounding so it adds up exactly

        # popularity-weighted pool of items to pick from
        pool = [item_id[n] for n, c, p, co, hs, av, d in ITEMS if av == 1]
        pool_w = [POPULARITY.get(n, 2) for n, c, p, co, hs, av, d in ITEMS if av == 1]
        price_cost = {item_id[n]: (p, co) for n, c, p, co, hs, av, d in ITEMS}

        for d, n_orders in zip(days, counts):
            for _ in range(n_orders):
                guest = random.choice(guest_ids) if random.random() < 0.6 else None
                hour = random.randint(11, 14) if random.random() < 0.45 else random.randint(17, 21)
                opened = datetime(d.year, d.month, d.day, hour, random.randint(0, 59))
                closed = opened + timedelta(minutes=random.randint(20, 75))
                ts, ts2 = opened.strftime("%Y-%m-%d %H:%M:%S"), closed.strftime("%Y-%m-%d %H:%M:%S")

                # pick 1-4 items; regulars usually order their favourites
                n_lines = random.choices([1, 2, 3, 4], weights=[20, 35, 30, 15])[0]
                picks = random.choices(pool, weights=pool_w, k=n_lines)
                if guest and random.random() < 0.65:
                    picks[0] = random.choice(favourites[guest])
                qty = {}
                for p in picks:
                    qty[p] = qty.get(p, 0) + 1

                total = sum(price_cost[p][0] * q for p, q in qty.items())
                cur = conn.execute("""
                    INSERT INTO orders (table_id, customer_id, status, opened_at, closed_at, total_amount)
                    VALUES (?, ?, 'closed', ?, ?, ?)
                """, (random.randint(1, 8), guest, ts, ts2, round(total, 2)))
                for p, q in qty.items():
                    price, cost = price_cost[p]
                    conn.execute("""
                        INSERT INTO order_items (order_id, item_id, quantity, unit_price, unit_cost)
                        VALUES (?, ?, ?, ?, ?)
                    """, (cur.lastrowid, p, q, price, cost))

        scoring.refresh_daily_item_sales(conn)

        # --- summary ---
        print("Seed complete!")
        for table in ["menu_items", "dining_tables", "customers", "customer_notes",
                      "orders", "order_items", "daily_item_sales"]:
            c = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
            print(f"  {table}: {c} rows")
        print("\nTop 5 items by units sold:")
        for r in conn.execute("""
            SELECT m.item_name, SUM(oi.quantity) AS qty,
                   ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
            FROM order_items oi JOIN menu_items m ON m.item_id = oi.item_id
            GROUP BY oi.item_id ORDER BY qty DESC LIMIT 5
        """):
            print(f"  {r['item_name']}: {r['qty']} sold, ${r['revenue']} revenue")


if __name__ == "__main__":
    run()