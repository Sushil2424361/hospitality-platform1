"""Hospitality Management Platform - Main FastAPI Application.

Staff-only API for order entry, guest cards, specials scoring, and reports.
Role-based access is enforced via the 'X-Role' header (Waiter, Manager, Owner).
"""
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import List, Optional
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import scoring, seed
from .db import get_conn, init_db

# Valid roles supported by the platform
VALID_ROLES = {"Waiter", "Manager", "Owner"}


def get_role(x_role: Optional[str] = Header(None, alias="X-Role")) -> str:
    """Validate the X-Role header and return the normalized role name."""
    if not x_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing 'X-Role' header. Allowed roles: Waiter, Manager, Owner."
        )
    normalized = x_role.strip().capitalize()
    if normalized not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid role '{x_role}'. Allowed roles: Waiter, Manager, Owner."
        )
    return normalized


def require_role(allowed_roles: set[str]):
    """Dependency factory that checks if the request role is permitted."""
    def checker(role: str = Depends(get_role)) -> str:
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' is not allowed to access this endpoint."
            )
        return role
    return checker


# Pydantic models for incoming request bodies
class OrderItemIn(BaseModel):
    item_id: int
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")
    item_note: Optional[str] = ""


class OrderCreate(BaseModel):
    table_id: int
    customer_id: Optional[int] = None
    items: List[OrderItemIn] = Field(..., min_length=1, description="Order must contain at least 1 item")


class NoteCreate(BaseModel):
    note_text: str = Field(..., min_length=1, description="Note text cannot be empty")


class SpecialPatch(BaseModel):
    status: Optional[str] = Field(None, pattern="^(suggested|approved|rejected)$")
    item_id: Optional[int] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run database initialization and auto-seeding on application startup."""
    init_db()
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM menu_items").fetchone()
        menu_count = row["c"] if row else 0

    if menu_count == 0:
        # Database has no menu items (e.g. fresh deploy or ephemeral Render disk)
        seed.run()

    yield


app = FastAPI(
    title="Hospitality Management Platform",
    description="Internal staff-only restaurant operations API",
    lifespan=lifespan
)

# Serve static assets from the static folder
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_home():
    """Serve the main static HTML page."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Hospitality Management Platform API active"}


# -----------------------------------------------------------------------------
# 1. Menu and Tables
# -----------------------------------------------------------------------------
@app.get("/api/menu")
def get_menu(role: str = Depends(require_role({"Waiter", "Manager", "Owner"}))):
    """List active menu items. Owners also see cost and margin per item."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT m.item_id, m.category_id, c.category_name, m.item_name,
                   m.description, m.price, m.cost, m.is_house_specialty,
                   m.is_available, m.is_active
            FROM menu_items m
            JOIN menu_categories c ON c.category_id = m.category_id
            WHERE m.is_active = 1
            ORDER BY c.sort_order, m.item_id
        """).fetchall()

    menu_list = []
    for r in rows:
        item = {
            "item_id": r["item_id"],
            "category_id": r["category_id"],
            "category_name": r["category_name"],
            "item_name": r["item_name"],
            "description": r["description"],
            "price": r["price"],
            "is_house_specialty": bool(r["is_house_specialty"]),
            "is_available": bool(r["is_available"]),
        }
        # Only owners see cost figures
        if role == "Owner":
            item["cost"] = r["cost"]
            margin = round((r["price"] - r["cost"]) / r["price"] * 100, 1) if r["price"] > 0 else 0.0
            item["margin_pct"] = margin
        menu_list.append(item)

    return menu_list


@app.get("/api/tables")
def get_tables(role: str = Depends(require_role({"Waiter", "Manager", "Owner"}))):
    """List all dining tables and seat counts."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT table_id, table_label, seats
            FROM dining_tables
            ORDER BY table_id
        """).fetchall()
    return [dict(r) for r in rows]


# -----------------------------------------------------------------------------
# 2. Order Entry
# -----------------------------------------------------------------------------
@app.post("/api/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    role: str = Depends(require_role({"Waiter", "Manager", "Owner"}))
):
    """Record an order: freezes unit_price and unit_cost from DB at time of sale."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_conn() as conn:
        # Validate table exists
        table = conn.execute(
            "SELECT table_id FROM dining_tables WHERE table_id = ?",
            (payload.table_id,)
        ).fetchone()
        if not table:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table ID {payload.table_id} does not exist."
            )

        # Validate customer exists if customer_id was provided
        if payload.customer_id is not None:
            customer = conn.execute(
                "SELECT customer_id FROM customers WHERE customer_id = ?",
                (payload.customer_id,)
            ).fetchone()
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Customer ID {payload.customer_id} does not exist."
                )

        # Validate all items exist and are available
        order_lines = []
        total_amount = 0.0

        for it in payload.items:
            item_row = conn.execute("""
                SELECT item_id, item_name, price, cost, is_available, is_active
                FROM menu_items WHERE item_id = ?
            """, (it.item_id,)).fetchone()

            if not item_row or not item_row["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Menu item ID {it.item_id} does not exist."
                )
            if not item_row["is_available"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Menu item '{item_row['item_name']}' is currently unavailable."
                )

            line_price = item_row["price"]
            line_cost = item_row["cost"]
            line_total = line_price * it.quantity
            total_amount += line_total

            order_lines.append({
                "item_id": it.item_id,
                "quantity": it.quantity,
                "unit_price": line_price,
                "unit_cost": line_cost,
                "item_note": it.item_note or ""
            })

        total_amount = round(total_amount, 2)

        # Insert order record (status 'closed' so it immediately counts towards sales & scoring)
        cur = conn.execute("""
            INSERT INTO orders (table_id, customer_id, status, opened_at, closed_at, total_amount)
            VALUES (?, ?, 'closed', ?, ?, ?)
        """, (payload.table_id, payload.customer_id, now_str, now_str, total_amount))
        order_id = cur.lastrowid

        # Insert order line items with frozen price and cost
        for line in order_lines:
            conn.execute("""
                INSERT INTO order_items (order_id, item_id, quantity, unit_price, unit_cost, item_note)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order_id, line["item_id"], line["quantity"],
                  line["unit_price"], line["unit_cost"], line["item_note"]))

        # Refresh daily sales rollups for scoring and dashboard
        scoring.refresh_daily_item_sales(conn)
        conn.commit()

        return {
            "order_id": order_id,
            "table_id": payload.table_id,
            "customer_id": payload.customer_id,
            "status": "closed",
            "total_amount": total_amount,
            "items_count": len(order_lines),
            "opened_at": now_str
        }


# -----------------------------------------------------------------------------
# 3. Guest Card
# -----------------------------------------------------------------------------
@app.get("/api/customers")
def search_customers(
    q: str = Query("", description="Search term for guest name or phone number"),
    role: str = Depends(require_role({"Waiter", "Manager", "Owner"}))
):
    """Search guests by name or phone number."""
    term = q.strip()
    with get_conn() as conn:
        if term:
            pattern = f"%{term}%"
            rows = conn.execute("""
                SELECT customer_id, full_name, phone, email, dietary_notes, created_at
                FROM customers
                WHERE is_anonymised = 0 AND (full_name LIKE ? OR phone LIKE ?)
                ORDER BY full_name
                LIMIT 50
            """, (pattern, pattern)).fetchall()
        else:
            rows = conn.execute("""
                SELECT customer_id, full_name, phone, email, dietary_notes, created_at
                FROM customers
                WHERE is_anonymised = 0
                ORDER BY customer_id DESC
                LIMIT 20
            """).fetchall()

    return [dict(r) for r in rows]


@app.get("/api/customers/{customer_id}/card")
def get_customer_card(
    customer_id: int,
    role: str = Depends(require_role({"Waiter", "Manager", "Owner"}))
):
    """Load guest profile, visit count, last visit, top 3 dishes, allergies, and notes in ONE call."""
    with get_conn() as conn:
        customer = conn.execute("""
            SELECT customer_id, full_name, phone, email, dietary_notes, created_at
            FROM customers
            WHERE customer_id = ? AND is_anonymised = 0
        """, (customer_id,)).fetchone()

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found."
            )

        # Visit statistics
        stats = conn.execute("""
            SELECT COUNT(*) AS visit_count, MAX(opened_at) AS last_visit
            FROM orders
            WHERE customer_id = ? AND status != 'voided'
        """, (customer_id,)).fetchone()

        # Top 3 ordered dishes
        top_dishes_rows = conn.execute("""
            SELECT m.item_name, SUM(oi.quantity) AS total_qty
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            JOIN menu_items m ON m.item_id = oi.item_id
            WHERE o.customer_id = ? AND o.status != 'voided'
            GROUP BY oi.item_id
            ORDER BY total_qty DESC
            LIMIT 3
        """, (customer_id,)).fetchall()

        # Staff notes (newest first)
        notes_rows = conn.execute("""
            SELECT note_id, author_role, note_text, created_at
            FROM customer_notes
            WHERE customer_id = ?
            ORDER BY note_id DESC
        """, (customer_id,)).fetchall()

    return {
        "customer_id": customer["customer_id"],
        "full_name": customer["full_name"],
        "phone": customer["phone"],
        "email": customer["email"],
        "dietary_notes": customer["dietary_notes"] or "",  # strictly from database, never generated
        "visit_count": stats["visit_count"] or 0,
        "last_visit": stats["last_visit"] or "Never",
        "top_dishes": [dict(r) for r in top_dishes_rows],
        "staff_notes": [dict(r) for r in notes_rows],
        "created_at": customer["created_at"]
    }


@app.post("/api/customers/{customer_id}/notes", status_code=status.HTTP_201_CREATED)
def add_customer_note(
    customer_id: int,
    payload: NoteCreate,
    role: str = Depends(require_role({"Waiter", "Manager", "Owner"}))
):
    """Add a new staff note to a guest card with author role recorded."""
    note_text = payload.note_text.strip()
    if not note_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note text cannot be empty."
        )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_conn() as conn:
        customer = conn.execute(
            "SELECT customer_id FROM customers WHERE customer_id = ?",
            (customer_id,)
        ).fetchone()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found."
            )

        cur = conn.execute("""
            INSERT INTO customer_notes (customer_id, author_role, note_text, created_at)
            VALUES (?, ?, ?, ?)
        """, (customer_id, role, note_text, now_str))
        conn.commit()
        note_id = cur.lastrowid

    return {
        "note_id": note_id,
        "customer_id": customer_id,
        "author_role": role,
        "note_text": note_text,
        "created_at": now_str
    }


# -----------------------------------------------------------------------------
# 4. Specials (Scoring & Approval)
# -----------------------------------------------------------------------------
@app.post("/api/specials/generate")
def generate_specials_endpoint(
    target_date: Optional[str] = Query(None, alias="date", description="Target date YYYY-MM-DD (defaults to tomorrow)"),
    role: str = Depends(require_role({"Manager", "Owner"}))
):
    """Generate tomorrow's scored specials suggestions with plain-English reasons (Manager and Owner only)."""
    if not target_date:
        target_date = (date.today() + timedelta(days=1)).isoformat()
    else:
        try:
            date.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Expected YYYY-MM-DD."
            )

    with get_conn() as conn:
        suggestions = scoring.generate_specials(conn, target_date)

    return {
        "date": target_date,
        "count": len(suggestions),
        "suggestions": suggestions
    }


@app.get("/api/specials")
def get_specials(
    specials_date: Optional[str] = Query(None, alias="date", description="Date YYYY-MM-DD (defaults to today)"),
    status_filter: Optional[str] = Query(None, alias="status", pattern="^(suggested|approved|rejected)$"),
    role: str = Depends(require_role({"Waiter", "Manager", "Owner"}))
):
    """Get specials suggestions for a given date."""
    target_date = specials_date or date.today().isoformat()

    query = """
        SELECT s.suggestion_id, s.for_date, s.score, s.reason_text, s.status,
               s.generated_at, m.item_id, m.item_name, m.price, m.description
        FROM special_suggestions s
        JOIN menu_items m ON m.item_id = s.item_id
        WHERE s.for_date = ?
    """
    params = [target_date]

    if status_filter:
        query += " AND s.status = ?"
        params.append(status_filter)

    query += " ORDER BY s.score DESC"

    with get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        # Fallback: if no specials for today and no explicit date was passed, check tomorrow
        if not rows and not specials_date:
            tomorrow_date = (date.today() + timedelta(days=1)).isoformat()
            fallback_params = [tomorrow_date]
            if status_filter:
                fallback_params.append(status_filter)
            rows = conn.execute(query, tuple(fallback_params)).fetchall()

    return [dict(r) for r in rows]


@app.patch("/api/specials/{suggestion_id}")
def update_special(
    suggestion_id: int,
    payload: SpecialPatch,
    role: str = Depends(require_role({"Manager", "Owner"}))
):
    """Approve, reject, or swap a special suggestion (Manager and Owner only)."""
    with get_conn() as conn:
        existing = conn.execute("""
            SELECT suggestion_id, for_date, item_id, status, reason_text, score
            FROM special_suggestions WHERE suggestion_id = ?
        """, (suggestion_id,)).fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Special suggestion ID {suggestion_id} not found."
            )

        new_status = payload.status or existing["status"]
        new_item_id = existing["item_id"]
        reason_text = existing["reason_text"]

        # Swap menu item if requested
        if payload.item_id is not None:
            new_item = conn.execute("""
                SELECT item_id, item_name, is_active, is_available
                FROM menu_items WHERE item_id = ?
            """, (payload.item_id,)).fetchone()

            if not new_item or not new_item["is_active"] or not new_item["is_available"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item ID {payload.item_id} is unavailable or does not exist."
                )
            new_item_id = payload.item_id
            reason_text = f"Swapped by {role} for {new_item['item_name']}."

            # Remove duplicate suggestion for same date and item if it exists
            conn.execute("""
                DELETE FROM special_suggestions
                WHERE for_date = ? AND item_id = ? AND suggestion_id != ?
            """, (existing["for_date"], new_item_id, suggestion_id))

        conn.execute("""
            UPDATE special_suggestions
            SET status = ?, item_id = ?, reason_text = ?
            WHERE suggestion_id = ?
        """, (new_status, new_item_id, reason_text, suggestion_id))
        conn.commit()

        updated = conn.execute("""
            SELECT s.suggestion_id, s.for_date, s.score, s.reason_text, s.status,
                   s.generated_at, m.item_id, m.item_name, m.price
            FROM special_suggestions s
            JOIN menu_items m ON m.item_id = s.item_id
            WHERE s.suggestion_id = ?
        """, (suggestion_id,)).fetchone()

    return dict(updated)


# -----------------------------------------------------------------------------
# 5. Dashboard Reports
# -----------------------------------------------------------------------------
@app.get("/api/reports/daily")
def get_daily_report(
    report_date: Optional[str] = Query(None, alias="date", description="Date YYYY-MM-DD (defaults to today)"),
    role: str = Depends(require_role({"Manager", "Owner"}))
):
    """Daily sales and order count. Owners also receive profit and margin figures."""
    target_date = report_date or date.today().isoformat()

    with get_conn() as conn:
        # Aggregated sales and orders for the day
        summary = conn.execute("""
            SELECT COUNT(*) AS order_count,
                   COALESCE(SUM(total_amount), 0.0) AS total_sales
            FROM orders
            WHERE date(closed_at) = ? AND status = 'closed'
        """, (target_date,)).fetchone()

        order_count = summary["order_count"] or 0
        total_sales = round(summary["total_sales"] or 0.0, 2)

        data = {
            "date": target_date,
            "order_count": order_count,
            "total_sales": total_sales,
        }

        # Owner-only profit margin figures
        if role == "Owner":
            cost_summary = conn.execute("""
                SELECT COALESCE(SUM(oi.quantity * oi.unit_cost), 0.0) AS total_cost
                FROM order_items oi
                JOIN orders o ON o.order_id = oi.order_id
                WHERE date(o.closed_at) = ? AND o.status = 'closed'
            """, (target_date,)).fetchone()

            total_cost = round(cost_summary["total_cost"] or 0.0, 2)
            total_profit = round(total_sales - total_cost, 2)
            margin_pct = round((total_profit / total_sales) * 100, 1) if total_sales > 0 else 0.0

            data["total_cost"] = total_cost
            data["total_profit"] = total_profit
            data["profit_margin_pct"] = margin_pct

    return data


@app.get("/api/reports/items")
def get_items_report(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    role: str = Depends(require_role({"Manager", "Owner"}))
):
    """Top 5 and bottom 5 selling items. Owners also receive margin figures per item."""
    where_clauses = ["o.status = 'closed'"]
    params = []

    if start_date:
        where_clauses.append("date(o.closed_at) >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("date(o.closed_at) <= ?")
        params.append(end_date)

    where_sql = " AND ".join(where_clauses)

    with get_conn() as conn:
        # Sales aggregated per item
        sql = f"""
            SELECT m.item_id, m.item_name, c.category_name, m.price, m.cost,
                   COALESCE(SUM(oi.quantity), 0) AS units_sold,
                   COALESCE(SUM(oi.quantity * oi.unit_price), 0.0) AS revenue,
                   COALESCE(SUM(oi.quantity * oi.unit_cost), 0.0) AS total_cost
            FROM menu_items m
            JOIN menu_categories c ON c.category_id = m.category_id
            LEFT JOIN order_items oi ON oi.item_id = m.item_id
            LEFT JOIN orders o ON o.order_id = oi.order_id AND {where_sql}
            WHERE m.is_active = 1
            GROUP BY m.item_id
        """
        all_items = conn.execute(sql, tuple(params)).fetchall()

    def format_item(row):
        units = row["units_sold"]
        rev = round(row["revenue"], 2)
        item_data = {
            "item_id": row["item_id"],
            "item_name": row["item_name"],
            "category_name": row["category_name"],
            "units_sold": units,
            "revenue": rev
        }
        if role == "Owner":
            cost = round(row["total_cost"], 2)
            profit = round(rev - cost, 2)
            margin_pct = round((profit / rev) * 100, 1) if rev > 0 else 0.0
            item_data["total_cost"] = cost
            item_data["profit"] = profit
            item_data["margin_pct"] = margin_pct
        return item_data

    # Sort to get top 5 and bottom 5
    sorted_items = sorted(all_items, key=lambda x: x["units_sold"], reverse=True)
    top_5 = [format_item(r) for r in sorted_items[:5]]
    bottom_5 = [format_item(r) for r in sorted(all_items, key=lambda x: x["units_sold"])[:5]]

    return {
        "top_5": top_5,
        "bottom_5": bottom_5
    }
