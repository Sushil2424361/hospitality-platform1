"""End-to-end endpoint tests for Hospitality Management Platform.

Runs against http://127.0.0.1:8000 using standard library urllib.
Tests all 11 endpoints, role permission checks, and data validation.
"""
import json
import urllib.error
import urllib.request
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8000"


def make_request(path, method="GET", data=None, headers=None):
    """Helper to send HTTP requests and return (status_code, response_dict_or_str)."""
    url = f"{BASE_URL}{path}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            content = resp.read().decode("utf-8")
            try:
                parsed = json.loads(content)
            except Exception:
                parsed = content
            return status, parsed
    except urllib.error.HTTPError as e:
        status = e.code
        content = e.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = content
        return status, parsed


def run_all_tests():
    passed = 0
    failed = 0

    def assert_eq(actual, expected, message):
        nonlocal passed, failed
        if actual == expected:
            passed += 1
            print(f"  [PASS] {message}")
        else:
            failed += 1
            print(f"  [FAIL] {message} - Expected {expected}, got {actual}")

    print("\n--- 1. Testing Static Assets & Root ---")
    st, res = make_request("/")
    assert_eq(st, 200, "Root '/' returns static index page (200)")
    st, res = make_request("/static/index.html")
    assert_eq(st, 200, "GET /static/index.html returns 200")

    print("\n--- 2. Testing Role Permissions (X-Role) ---")
    # Missing header
    st, res = make_request("/api/menu")
    assert_eq(st, 403, "Missing X-Role returns 403 Forbidden")

    # Invalid role
    st, res = make_request("/api/menu", headers={"X-Role": "Chef"})
    assert_eq(st, 403, "Invalid role 'Chef' returns 403 Forbidden")

    # Waiter cannot generate specials
    st, res = make_request("/api/specials/generate", method="POST", headers={"X-Role": "Waiter"})
    assert_eq(st, 403, "Waiter role cannot POST /api/specials/generate (403)")

    # Waiter cannot patch specials
    st, res = make_request("/api/specials/1", method="PATCH", data={"status": "approved"}, headers={"X-Role": "Waiter"})
    assert_eq(st, 403, "Waiter role cannot PATCH /api/specials/{id} (403)")

    # Waiter cannot view daily reports
    st, res = make_request("/api/reports/daily", headers={"X-Role": "Waiter"})
    assert_eq(st, 403, "Waiter role cannot GET /api/reports/daily (403)")

    # Waiter cannot view item reports
    st, res = make_request("/api/reports/items", headers={"X-Role": "Waiter"})
    assert_eq(st, 403, "Waiter role cannot GET /api/reports/items (403)")

    print("\n--- 3. Testing Menu & Tables ---")
    # Waiter gets menu without cost
    st, menu_waiter = make_request("/api/menu", headers={"X-Role": "Waiter"})
    assert_eq(st, 200, "GET /api/menu returns 200 for Waiter")
    assert_eq(len(menu_waiter), 34, f"Menu has 34 items (got {len(menu_waiter)})")
    has_cost = any("cost" in item for item in menu_waiter)
    assert_eq(has_cost, False, "Menu for Waiter does NOT expose cost figures")

    # Owner gets menu WITH cost and margin
    st, menu_owner = make_request("/api/menu", headers={"X-Role": "Owner"})
    assert_eq(st, 200, "GET /api/menu returns 200 for Owner")
    owner_has_cost = all("cost" in item and "margin_pct" in item for item in menu_owner)
    assert_eq(owner_has_cost, True, "Menu for Owner exposes cost and margin_pct")

    # Tables list
    st, tables = make_request("/api/tables", headers={"X-Role": "Waiter"})
    assert_eq(st, 200, "GET /api/tables returns 200")
    assert_eq(len(tables), 8, f"Tables endpoint returned {len(tables)} tables (expected 8)")

    print("\n--- 4. Testing Order Placement ---")
    # Unavailable item test (Item 34 is 'Elaneer (Tender Coconut)' which is unavailable)
    order_bad = {
        "table_id": 1,
        "items": [{"item_id": 34, "quantity": 1}]
    }
    st, res = make_request("/api/orders", method="POST", data=order_bad, headers={"X-Role": "Waiter"})
    assert_eq(st, 400, "POST /api/orders with unavailable item (Elaneer) rejects with 400 Bad Request")

    # Valid order placement
    order_good = {
        "table_id": 2,
        "customer_id": 1,
        "items": [
            {"item_id": 1, "quantity": 2, "item_note": "Extra crispy"},
            {"item_id": 7, "quantity": 1, "item_note": "Crispy and hot"}
        ]
    }
    st, order_res = make_request("/api/orders", method="POST", data=order_good, headers={"X-Role": "Waiter"})
    assert_eq(st, 201, "POST /api/orders saves valid order (201 Created)")
    assert_eq(order_res.get("status"), "closed", "Order status is 'closed'")
    assert_eq("order_id" in order_res, True, f"Order assigned order_id {order_res.get('order_id')}")

    print("\n--- 5. Testing Guest Card & Notes ---")
    # Search customers
    st, custs = make_request("/api/customers?q=Anna", headers={"X-Role": "Waiter"})
    assert_eq(st, 200, "GET /api/customers?q=Anna returns 200")
    assert_eq(len(custs) > 0, True, f"Found {len(custs)} customer(s) matching 'Anna'")

    # Single-call guest card
    st, card = make_request("/api/customers/1/card", headers={"X-Role": "Waiter"})
    assert_eq(st, 200, "GET /api/customers/1/card returns 200")
    assert_eq("full_name" in card, True, f"Guest card has name: {card.get('full_name')}")
    assert_eq("visit_count" in card, True, f"Guest card has visit_count: {card.get('visit_count')}")
    assert_eq("last_visit" in card, True, f"Guest card has last_visit: {card.get('last_visit')}")
    assert_eq("top_dishes" in card, True, f"Guest card has top_dishes (count: {len(card.get('top_dishes', []))})")
    assert_eq("dietary_notes" in card, True, f"Guest card has dietary_notes: '{card.get('dietary_notes')}'")
    assert_eq("staff_notes" in card, True, f"Guest card has staff_notes (count: {len(card.get('staff_notes', []))})")

    # Add staff note
    st, note_res = make_request("/api/customers/1/notes", method="POST",
                                data={"note_text": "Guest requested extra ice with drinks."},
                                headers={"X-Role": "Waiter"})
    assert_eq(st, 201, "POST /api/customers/1/notes creates staff note (201 Created)")
    assert_eq(note_res.get("author_role"), "Waiter", "Author role recorded as 'Waiter'")

    print("\n--- 6. Testing Specials Scoring & Management ---")
    # Generate specials (Manager)
    st, gen_res = make_request("/api/specials/generate", method="POST", headers={"X-Role": "Manager"})
    assert_eq(st, 200, "POST /api/specials/generate runs scoring and returns suggestions (200)")
    sugg_count = gen_res.get("count", 0)
    assert_eq(sugg_count > 0, True, f"Generated {sugg_count} specials suggestions")

    # View specials
    target_date = gen_res.get("date")
    st, specials_list = make_request(f"/api/specials?date={target_date}", headers={"X-Role": "Waiter"})
    assert_eq(st, 200, f"GET /api/specials?date={target_date} returns 200")
    first_special = specials_list[0] if specials_list else {}
    sugg_id = first_special.get("suggestion_id")

    # Patch special: Approve
    if sugg_id:
        st, patch_res = make_request(f"/api/specials/{sugg_id}", method="PATCH",
                                     data={"status": "approved"}, headers={"X-Role": "Manager"})
        assert_eq(st, 200, f"PATCH /api/specials/{sugg_id} status to 'approved' returns 200")
        assert_eq(patch_res.get("status"), "approved", "Special status updated to 'approved'")

        # Patch special: Swap item (swap to Item 3: Steamed Idli (Pair))
        st, swap_res = make_request(f"/api/specials/{sugg_id}", method="PATCH",
                                    data={"item_id": 3}, headers={"X-Role": "Manager"})
        assert_eq(st, 200, f"PATCH /api/specials/{sugg_id} swapped item to Steamed Idli (Pair) (200)")
        assert_eq(swap_res.get("item_id"), 3, "Special item_id updated to 3")

    print("\n--- 7. Testing Reports ---")
    # Daily report as Manager (no profit margin figures)
    st, rep_mgr = make_request("/api/reports/daily", headers={"X-Role": "Manager"})
    assert_eq(st, 200, "GET /api/reports/daily returns 200 for Manager")
    assert_eq("total_sales" in rep_mgr, True, f"Manager sees total_sales: ₹{rep_mgr.get('total_sales')}")
    assert_eq("total_cost" in rep_mgr, False, "Manager does NOT see total_cost")
    assert_eq("profit_margin_pct" in rep_mgr, False, "Manager does NOT see profit_margin_pct")

    # Daily report as Owner (with profit margin figures)
    st, rep_own = make_request("/api/reports/daily", headers={"X-Role": "Owner"})
    assert_eq(st, 200, "GET /api/reports/daily returns 200 for Owner")
    assert_eq("total_cost" in rep_own, True, f"Owner sees total_cost: ₹{rep_own.get('total_cost')}")
    assert_eq("total_profit" in rep_own, True, f"Owner sees total_profit: ₹{rep_own.get('total_profit')}")
    assert_eq("profit_margin_pct" in rep_own, True, f"Owner sees profit_margin_pct: {rep_own.get('profit_margin_pct')}%")

    # Items report as Manager (no margin figures)
    st, items_mgr = make_request("/api/reports/items", headers={"X-Role": "Manager"})
    assert_eq(st, 200, "GET /api/reports/items returns 200 for Manager")
    assert_eq(len(items_mgr.get("top_5", [])), 5, "Manager sees top 5 items")
    assert_eq(len(items_mgr.get("bottom_5", [])), 5, "Manager sees bottom 5 items")
    assert_eq("margin_pct" in items_mgr["top_5"][0], False, "Manager does NOT see margin_pct in top 5")

    # Items report as Owner (with margin figures)
    st, items_own = make_request("/api/reports/items", headers={"X-Role": "Owner"})
    assert_eq(st, 200, "GET /api/reports/items returns 200 for Owner")
    assert_eq("margin_pct" in items_own["top_5"][0], True, f"Owner sees margin_pct in top 5: {items_own['top_5'][0].get('margin_pct')}%")
    assert_eq("profit" in items_own["top_5"][0], True, f"Owner sees profit in top 5: ₹{items_own['top_5'][0].get('profit')}")

    print(f"\n==========================================")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"==========================================")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
