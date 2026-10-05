# Hospitality Management Platform: standing instructions

## What this is
An internal web app (PWA) for small restaurants. Staff only; guests never log
in. It records orders and guest preferences, suggests next-day specials from
sales data, and gives waiters a "guest card" so they can serve returning
guests personally. AI assists; humans decide.

## About the developer
I am a BEGINNER. Write ALL code. Explain things in simple words. Never leave
placeholders like "..." or "rest of code here". Keep code short, readable and
lightly commented. Do not add features I did not ask for.

## Tech (fixed)
- Backend: Python 3.11, FastAPI, SQLite (sqlite3, no ORM), uvicorn
- Frontend: plain HTML + vanilla JavaScript + Tailwind CSS via CDN.
  NO React, NO Node, NO npm, NO build step.
- Must run smoothly on LOW-RAM phones: small pages, no heavy libraries, no
  big charts, paginate long lists, mobile-first, large tap targets.
- Installable PWA (manifest + simple service worker). Never cache /api.
- I use Windows. Give Windows commands first.

## Roles (no real login)
Role dropdown in the top bar: Waiter, Manager, Owner, saved in localStorage
and sent as header "X-Role" on every API call. The API returns 403 when a
role is not allowed.
- Waiter: order entry, guest card, today's specials (read only)
- Manager: also specials approval and dashboard
- Owner: everything, plus profit margin figures

## The 4 features (build only these)
1. Order entry: table, menu items and quantities, optional guest, save.
   Store unit_price and unit_cost on each order line. Unavailable items are
   greyed out.
2. Guest card: search by name or phone; show visit count, last visit, top 3
   dishes, dietary notes/allergies (in red), staff notes with an add-note
   box. Loaded with ONE API call.
3. Specials: "Generate tomorrow's specials" runs scoring and lists ranked
   suggestions with plain-English reasons. Manager can Approve, Reject or
   Swap. Approved specials show next to house specialties on the order screen.
4. Dashboard: today's sales and order count, top 5 and bottom 5 items, margin
   per item (Owner only). Simple tables; optional tiny bar chart in plain
   HTML/CSS.

## Specials score (app/scoring.py)
score = 0.5*volume + 0.3*margin + 0.2*trend - 0.25*recently_featured
(each part normalised 0 to 1; volume = 7-day average units; trend = last 3
days vs previous 4 days; exclude house specialties and unavailable items;
save a plain-English reason for each suggestion)

## Safety rules
- Parameterised SQL only. Validate all inputs.
- Dietary/allergy data comes ONLY from stored fields, never generated.
- Never put secrets or API keys in code. Use a .env file listed in .gitignore.
- Never delete files or run destructive commands without asking me first.
- After each task: tell me exactly how to run it and give 3 manual tests.