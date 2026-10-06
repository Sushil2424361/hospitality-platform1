"""Seed the database with authentic South Indian demo data for Dakshin Flavors.

Run from the project folder:  python -m app.seed
Creates ~2,000 closed orders over the last 30 days with repeat guests.
"""
import random
import sys
from datetime import date, datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .db import get_conn, init_db
from . import scoring

random.seed(42)  # consistent demo data across runs

CATEGORIES = [
    ("Starters & Small Bites", 1),
    ("Tiffin Mains", 2),
    ("Rice & Specialty Mains", 3),
    ("Traditional Desserts", 4),
    ("Traditional Beverages", 5),
]

# (name, category, price in INR, assumed cost in INR, is_house_specialty, is_available, description)
ITEMS = [
    # 1. Starters & Small Bites (sort_order = 1)
    ("Medu Vada (Single)", "Starters & Small Bites", 35, 12, 0, 1, "Crisp urad dal doughnut with pepper, ginger, curry leaves"),
    ("Parippu / Masala Vada", "Starters & Small Bites", 35, 11, 0, 1, "Coarse Bengal gram fritters with shallots, fennel, red chilies"),
    ("Steamed Idli (Pair)", "Starters & Small Bites", 40, 14, 0, 1, "Steamed rice and lentil cakes with sambar and coconut chutney"),
    ("Mangalore / Mysore Bonda", "Starters & Small Bites", 45, 16, 0, 1, "Crisp flour-curd fritters with cumin, green chilies, coconut"),
    ("Upma / Khara Bath", "Starters & Small Bites", 45, 15, 0, 1, "Roasted semolina with mustard seeds, curry leaves, vegetables"),
    ("Paniyaram / Paddu (6 pcs)", "Starters & Small Bites", 60, 20, 0, 1, "Crisp-edged batter dumplings with onions, chilies, curry leaves"),
    ("Gobi / Veg 65", "Starters & Small Bites", 70, 26, 0, 1, "Crispy batter-fried florets in fiery South Indian masala"),
    ("Pepper Mushroom Fry", "Starters & Small Bites", 75, 30, 0, 1, "Button mushrooms roasted with crushed black pepper and shallots"),

    # 2. Tiffin Mains (sort_order = 2)
    ("Ven / Khara Pongal", "Tiffin Mains", 65, 22, 0, 1, "Rice and moong dal porridge with cashews, cumin, ghee"),
    ("Poori Saagu / Masala", "Tiffin Mains", 70, 25, 0, 1, "Two puffed pooris with potato bhaji or vegetable coconut saagu"),
    ("Malabar Parotta with Kurma", "Tiffin Mains", 70, 26, 0, 1, "Two flaky parottas with coconut cashew vegetable kurma"),
    ("Set Dosa (3 pcs)", "Tiffin Mains", 75, 25, 0, 1, "Three soft dosas with mixed vegetable kurma and chutney"),
    ("Masala Dosa", "Tiffin Mains", 80, 28, 0, 1, "Crispy crepe with potato-onion masala, sambar, coconut chutney"),
    ("Uttapam (Onion / Tomato)", "Tiffin Mains", 80, 27, 0, 1, "Thick pancake topped with onions, tomatoes, chilies, cilantro"),
    ("Puttu with Kadala Curry", "Tiffin Mains", 80, 26, 0, 1, "Steamed rice flour and coconut cylinders with Kerala chickpea gravy"),
    ("Rava Dosa", "Tiffin Mains", 85, 31, 0, 1, "Lacy semolina and rice flour crepe with cumin, pepper, chilies"),

    # 3. Rice & Specialty Mains (sort_order = 3)
    ("Curd Rice (Thayir Sadam)", "Rice & Specialty Mains", 60, 19, 0, 1, "Rice with curd, mustard seeds, curry leaves, ginger, pomegranate"),
    ("Lemon Rice (Chitranna)", "Rice & Specialty Mains", 60, 20, 0, 1, "Turmeric rice with roasted peanuts, lentils, chilies, lime"),
    ("Bisi Bele Bath", "Rice & Specialty Mains", 75, 27, 0, 1, "Karnataka rice, toor dal and vegetables in tamarind and ghee"),
    ("Vatha Kuzhambu Rice", "Rice & Specialty Mains", 80, 28, 0, 1, "Ponni rice with tamarind gravy, turkey berries, gingelly oil"),
    ("Mysore Masala Dosa", "Rice & Specialty Mains", 95, 33, 1, 1, "Crispy crepe with red chili-garlic paste and potato masala"),
    ("Kothu Parotta (Veg / Egg)", "Rice & Specialty Mains", 100, 39, 0, 1, "Shredded parotta stir-fried with onions, tomatoes, salna gravy"),
    ("South Indian Full Meals Thali", "Rice & Specialty Mains", 110, 52, 1, 1, "Unlimited rice on banana leaf with kootu, poriyal, sambar, rasam, curd, appalam, pickle"),

    # 4. Traditional Desserts (sort_order = 4)
    ("Rava Kesari / Kesari Bath", "Traditional Desserts", 45, 15, 0, 1, "Semolina halwa in ghee with cardamom, saffron, cashews"),
    ("Semiya / Rice Payasam", "Traditional Desserts", 40, 13, 0, 1, "Creamy kheer with vermicelli or rice, cardamom, raisins"),
    ("Mysore Pak (2 pcs)", "Traditional Desserts", 40, 14, 0, 1, "Gram flour, sugar syrup and ghee confection"),
    ("Sweet Paniyaram (Appe, 5 pcs)", "Traditional Desserts", 50, 16, 0, 1, "Dumplings with palm jaggery, coconut, cardamom"),

    # 5. Traditional Beverages (sort_order = 5)
    ("Neer Moru / Majjiga", "Traditional Beverages", 20, 5, 0, 1, "Chilled buttermilk with ginger, green chili, cumin, curry leaves"),
    ("Sulaimani Tea", "Traditional Beverages", 20, 5, 0, 1, "Hot Malabar spiced black tea with cardamom, cloves, lemon"),
    ("Filter Kaapi", "Traditional Beverages", 25, 7, 1, 1, "Hot chicory coffee with frothed milk"),
    ("Panakam", "Traditional Beverages", 25, 6, 0, 1, "Chilled jaggery, black pepper, dry ginger and cardamom cooler"),
    ("Sukku Malli Coffee", "Traditional Beverages", 25, 7, 0, 1, "Hot herbal brew of dry ginger, coriander seeds, palm jaggery"),
    ("Nannari Sarbath", "Traditional Beverages", 30, 8, 0, 1, "Chilled sarsaparilla root, lime juice and sabja seeds"),
    ("Elaneer (Tender Coconut)", "Traditional Beverages", 45, 13, 0, 0, "Chilled tender coconut water"),
]

FIRST = ["Anna", "Marco", "Sofia", "James", "Lucia", "Tom", "Elena", "Raj", "Mia",
         "Liam", "Olivia", "Noah", "Emma", "Lucas", "Grace", "Henry", "Chloe",
         "Diego", "Yuki", "Priya"]
LAST = ["Rossi", "Smith", "Kim", "Garcia", "Muller", "Brown", "Silva", "Patel",
        "Chen", "Jones", "Bianchi", "Taylor", "Costa", "Nguyen", "Khan", "Moretti",
        "Evans", "Santos", "Tanaka", "Sharma"]

# South Indian specific dietary notes (assigned to ~15 of 40 guests)
DIETARY = [
    "Peanut allergy (avoid Lemon Rice)",
    "Gluten sensitive (avoid semolina items)",
    "Lactose intolerant",
    "Egg allergy",
    "Less spicy please",
    "Jain, no onion or garlic",
    "Tree nut allergy (avoid payasam/kesari)",
    "Peanut and sesame allergy",
    "Diabetic - low sugar / no sweets",
    "Vegan (no ghee or curd)",
    "Mild spices only",
    "Strict Jain (no root vegetables)",
    "Gluten allergy (no rava / parotta)",
    "Dairy allergy (no curd, ghee, milk)",
    "Lactose intolerant (prefer black tea or neer moru)"
]

STAFF_NOTES = [
    "Prefers crispy dosa with minimal oil.",
    "Likes extra strong filter kaapi with less sugar.",
    "Always requests extra coconut chutney.",
    "Prefers a quiet corner table near window.",
    "Birthday regular - offer a complimentary Kesari Bath.",
    "Double-check peanut allergy with kitchen before serving Lemon Rice.",
    "Prefers warm drinking water on arrival.",
    "Likes curd rice served chilled with extra pomegranate.",
    "Family regular - usually orders Set Dosa and Idli pair.",
    "Prefers mild sambar without red chili seeds."
]

TABLES = [("T1", 2), ("T2", 2), ("T3", 4), ("T4", 4),
          ("T5", 6), ("T6", 4), ("T7", 8), ("T8", 2)]

# Item popularity weights for realistic sales distribution
POPULARITY = {
    # High popularity favourites
    "Filter Kaapi": 14,
    "Masala Dosa": 12,
    "Steamed Idli (Pair)": 11,
    "Medu Vada (Single)": 10,
    "South Indian Full Meals Thali": 9,

    # Moderate popularity
    "Ven / Khara Pongal": 7,
    "Poori Saagu / Masala": 7,
    "Set Dosa (3 pcs)": 6,
    "Rava Dosa": 6,
    "Bisi Bele Bath": 6,
    "Mysore Masala Dosa": 6,
    "Malabar Parotta with Kurma": 5,
    "Uttapam (Onion / Tomato)": 5,
    "Curd Rice (Thayir Sadam)": 5,
    "Lemon Rice (Chitranna)": 5,
    "Neer Moru / Majjiga": 5,
    "Rava Kesari / Kesari Bath": 4,
    "Kothu Parotta (Veg / Egg)": 4,
    "Gobi / Veg 65": 4,
    "Mangalore / Mysore Bonda": 4,
    "Parippu / Masala Vada": 4,
    "Paniyaram / Paddu (6 pcs)": 4,
    "Upma / Khara Bath": 3,
    "Puttu with Kadala Curry": 3,
    "Semiya / Rice Payasam": 3,
    "Mysore Pak (2 pcs)": 3,
    "Sulaimani Tea": 3,
    "Panakam": 3,
    "Sukku Malli Coffee": 3,
    "Nannari Sarbath": 3,

    # Less popular
    "Pepper Mushroom Fry": 1,
    "Vatha Kuzhambu Rice": 1,
    "Sweet Paniyaram (Appe, 5 pcs)": 1,
}


def run():
    init_db()
    with get_conn() as conn:
        # Clear existing demo data first to ensure seeding is safe to rerun idempotently
        conn.execute("DELETE FROM order_items")
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM customer_notes")
        conn.execute("DELETE FROM customers")
        conn.execute("DELETE FROM daily_item_sales")
        conn.execute("DELETE FROM special_suggestions")
        conn.execute("DELETE FROM dining_tables")
        conn.execute("DELETE FROM menu_items")
        conn.execute("DELETE FROM menu_categories")

        # --- Categories ---
        cat_id = {}
        for name, sort in CATEGORIES:
            cur = conn.execute(
                "INSERT INTO menu_categories (category_name, sort_order) VALUES (?, ?)",
                (name, sort)
            )
            cat_id[name] = cur.lastrowid

        # --- Menu Items ---
        item_id = {}
        for name, cat, price, cost, hs, avail, desc in ITEMS:
            cur = conn.execute("""
                INSERT INTO menu_items (category_id, item_name, description, price, cost,
                                        is_house_specialty, is_available, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (cat_id[cat], name, desc, price, cost, hs, avail))
            item_id[name] = cur.lastrowid

        # --- Dining Tables (8 tables T1-T8) ---
        for label, seats in TABLES:
            conn.execute("INSERT INTO dining_tables (table_label, seats) VALUES (?, ?)",
                         (label, seats))

        # --- 40 Guests (15 with realistic dietary notes) ---
        guest_ids = []
        favourites = {}
        sellable = [item_id[n] for n, c, p, co, hs, av, d in ITEMS if av == 1]
        names = [f"{f} {l}" for l in LAST[:2] for f in FIRST]  # 40 unique names
        for i in range(40):
            full_name = names[i]
            dietary = DIETARY[i] if i < len(DIETARY) else ""
            created = (date.today() - timedelta(days=random.randint(40, 400))).isoformat()
            cur = conn.execute("""
                INSERT INTO customers (full_name, phone, email, dietary_notes,
                                       consent_given, consent_date, created_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
            """, (full_name, f"555-01{10 + i}",
                  full_name.lower().replace(" ", ".") + "@example.com",
                  dietary, created, created))
            gid = cur.lastrowid
            guest_ids.append(gid)
            favourites[gid] = random.sample(sellable, 2)

        # 12 staff notes on random guests
        for _ in range(12):
            conn.execute("""
                INSERT INTO customer_notes (customer_id, author_role, note_text, created_at)
                VALUES (?, ?, ?, ?)
            """, (random.choice(guest_ids), random.choice(["Waiter", "Manager"]),
                  random.choice(STAFF_NOTES),
                  (date.today() - timedelta(days=random.randint(1, 20))).isoformat() + " 13:00:00"))

        # --- ~2,000 closed orders over the last 30 days ---
        today = date.today()
        days = [today - timedelta(days=i) for i in range(29, -1, -1)]
        # Weekends busier (Friday, Saturday 1.6x, Sunday 1.3x)
        weights = [1.6 if d.weekday() in (4, 5) else 1.3 if d.weekday() == 6 else 1.0
                   for d in days]
        wsum = sum(weights)
        counts = [round(2000 * w / wsum) for w in weights]
        counts[0] += 2000 - sum(counts)  # adjust rounding difference

        pool = [item_id[n] for n, c, p, co, hs, av, d in ITEMS if av == 1]
        pool_w = [POPULARITY.get(n, 2) for n, c, p, co, hs, av, d in ITEMS if av == 1]
        price_cost = {item_id[n]: (p, co) for n, c, p, co, hs, av, d in ITEMS}

        thali_id = item_id.get("South Indian Full Meals Thali")

        for d, n_orders in zip(days, counts):
            for _ in range(n_orders):
                guest = random.choice(guest_ids) if random.random() < 0.6 else None

                # Busy meal hours: Breakfast (7-11am 38%), Lunch (12-2pm 42%), Evening (5-9pm 20%)
                meal_slot = random.random()
                if meal_slot < 0.38:
                    hour = random.randint(7, 10)
                elif meal_slot < 0.80:
                    hour = random.randint(12, 14)
                else:
                    hour = random.randint(17, 21)

                opened = datetime(d.year, d.month, d.day, hour, random.randint(0, 59))
                closed = opened + timedelta(minutes=random.randint(20, 60))
                ts, ts2 = opened.strftime("%Y-%m-%d %H:%M:%S"), closed.strftime("%Y-%m-%d %H:%M:%S")

                # Most tickets have 1 to 4 items
                n_lines = random.choices([1, 2, 3, 4], weights=[20, 40, 25, 15])[0]
                picks = random.choices(pool, weights=pool_w, k=n_lines)

                # Lunch rush boost for Full Meals Thali
                if hour in (12, 13, 14) and thali_id and random.random() < 0.35:
                    picks[0] = thali_id

                # Regulars frequently order their favourites
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

        # --- Specials generation: approve top 3 for tomorrow and today ---
        tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
        tomorrow_specials = scoring.generate_specials(conn, tomorrow_str)
        for s in tomorrow_specials[:3]:
            conn.execute(
                "UPDATE special_suggestions SET status = 'approved' WHERE suggestion_id = ?",
                (s["suggestion_id"],)
            )

        today_str = date.today().isoformat()
        today_specials = scoring.generate_specials(conn, today_str)
        for s in today_specials[:3]:
            conn.execute(
                "UPDATE special_suggestions SET status = 'approved' WHERE suggestion_id = ?",
                (s["suggestion_id"],)
            )

        conn.commit()

        # Summary logging
        print("Dakshin Flavors demo seed complete!")
        for table in ["menu_categories", "menu_items", "dining_tables", "customers", "customer_notes",
                      "orders", "order_items", "daily_item_sales", "special_suggestions"]:
            c = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
            print(f"  {table}: {c} rows")
        print("\nTop 5 items by units sold:")
        for r in conn.execute("""
            SELECT m.item_name, SUM(oi.quantity) AS qty,
                   ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
            FROM order_items oi JOIN menu_items m ON m.item_id = oi.item_id
            GROUP BY oi.item_id ORDER BY qty DESC LIMIT 5
        """):
            print(f"  {r['item_name']}: {r['qty']} sold, ₹{r['revenue']} revenue")


if __name__ == "__main__":
    run()