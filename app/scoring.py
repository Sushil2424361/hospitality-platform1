"""Specials scoring: picks the best menu items to suggest as tomorrow's specials.

score = 0.5*volume + 0.3*margin + 0.2*trend - 0.25*recently_featured
(every part is normalised to 0..1 before weighting)
"""
from datetime import date, datetime, timedelta


def refresh_daily_item_sales(conn):
    """Rebuild the per-day, per-item sales summary from closed orders (upsert)."""
    conn.execute("""
        INSERT INTO daily_item_sales (sale_date, item_id, quantity_sold, revenue, total_cost)
        SELECT date(o.closed_at), oi.item_id,
               SUM(oi.quantity),
               SUM(oi.quantity * oi.unit_price),
               SUM(oi.quantity * oi.unit_cost)
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.status = 'closed' AND o.closed_at IS NOT NULL
        GROUP BY date(o.closed_at), oi.item_id
        ON CONFLICT(sale_date, item_id) DO UPDATE SET
            quantity_sold = excluded.quantity_sold,
            revenue       = excluded.revenue,
            total_cost    = excluded.total_cost
    """)
    conn.commit()


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _reason(b):
    """Plain-English explanation a manager can read at a glance."""
    pct = round(b["change"] * 100)
    if pct >= 10:
        first = f"Sold {pct}% above its weekly average"
    elif b["avg"] >= 3:
        first = "A steady seller all week"
    else:
        first = "Quiet but promising sales"
    reason = f"{first} and has a {round(b['margin'] * 100)}% margin"
    if b["featured"]:
        reason += " (featured as a special in the last 2 days, so scored lower)"
    return reason + "."


def generate_specials(conn, for_date_str, top_n=5):
    """Score every sellable item, keep the best `top_n` as suggestions."""
    refresh_daily_item_sales(conn)
    for_date = date.fromisoformat(for_date_str)
    # the 7 days BEFORE for_date, newest first: [d-1, d-2, ..., d-7]
    days7 = [(for_date - timedelta(days=i)).isoformat() for i in range(1, 8)]

    items = conn.execute("""
        SELECT item_id, item_name, price, cost FROM menu_items
        WHERE is_active = 1 AND is_available = 1 AND is_house_specialty = 0
    """).fetchall()

    # units sold per item per day over the last 7 days
    sales = {}
    for row in conn.execute("""
        SELECT item_id, sale_date, quantity_sold FROM daily_item_sales
        WHERE sale_date BETWEEN ? AND ?
    """, (days7[-1], days7[0])):
        sales.setdefault(row["item_id"], {})[row["sale_date"]] = row["quantity_sold"]

    # items that were approved specials in the last 2 days (penalised)
    recent = {r["item_id"] for r in conn.execute("""
        SELECT DISTINCT item_id FROM special_suggestions
        WHERE status = 'approved' AND for_date BETWEEN ? AND ?
    """, ((for_date - timedelta(days=2)).isoformat(),
          (for_date - timedelta(days=1)).isoformat()))}

    # first pass: weekly stats per item (needed to normalise volume)
    stats = {}
    for it in items:
        per_day = [sales.get(it["item_id"], {}).get(d, 0) for d in days7]
        stats[it["item_id"]] = {
            "avg":   sum(per_day) / 7,          # 7-day moving average
            "last3": sum(per_day[:3]) / 3,      # most recent 3 days
            "prev4": sum(per_day[3:]) / 4,      # the 4 days before that
        }
    max_avg = max((s["avg"] for s in stats.values()), default=0) or 1

    # second pass: compute the weighted score per item
    scored = []
    for it in items:
        s = stats[it["item_id"]]
        volume = s["avg"] / max_avg                                # 0..1
        margin = _clamp((it["price"] - it["cost"]) / it["price"])  # 0..1
        change = (s["last3"] - s["prev4"]) / (s["prev4"] or 1)     # 0.4 = +40%
        trend = _clamp((change + 1) / 2)                           # -100%..+100% -> 0..1
        featured = 1 if it["item_id"] in recent else 0
        score = 0.5 * volume + 0.3 * margin + 0.2 * trend - 0.25 * featured
        scored.append({
            "item_id": it["item_id"], "item_name": it["item_name"],
            "score": round(score, 4), "change": change, "avg": s["avg"],
            "margin": margin, "featured": featured,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    best = scored[:top_n]

    # wipe old un-actioned suggestions for that date, then store the new ones
    conn.execute("DELETE FROM special_suggestions WHERE for_date = ? AND status = 'suggested'",
                 (for_date_str,))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for b in best:
        conn.execute("""
            INSERT INTO special_suggestions (for_date, item_id, score, reason_text, status, generated_at)
            VALUES (?, ?, ?, ?, 'suggested', ?)
            ON CONFLICT(for_date, item_id) DO UPDATE SET
                score = excluded.score, reason_text = excluded.reason_text,
                status = 'suggested', generated_at = excluded.generated_at
        """, (for_date_str, b["item_id"], b["score"], _reason(b), now))
    conn.commit()

    rows = conn.execute("""
        SELECT s.suggestion_id, s.for_date, s.score, s.reason_text, s.status,
               m.item_id, m.item_name, m.price
        FROM special_suggestions s
        JOIN menu_items m ON m.item_id = s.item_id
        WHERE s.for_date = ?
        ORDER BY s.score DESC
    """, (for_date_str,)).fetchall()
    return [dict(r) for r in rows]