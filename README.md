# Dakshin Flavors, powered by Manajerz

This app is built on the Manajerz platform.
An internal, mobile-first Progressive Web App (PWA) designed for staff operations in small restaurants and South Indian Darshini tiffin centers. 

> **Core Philosophy**: *"AI assists, humans decide."*  
> Staff record orders, look up returning guest preferences, review algorithmic daily specials suggestions, and track real-time profitability—all with zero login friction on low-RAM smartphones. Guests never log in.

---

## The 4 Core Features

1. **Order Entry**: Quick-tap ordering with table selection, quantity steppers, optional guest linking, and kitchen item notes. Unit price and cost are frozen at time of sale. Unavailable items (e.g., *Set Dosa*) are greyed out. Approved daily specials show prominently next to house specialties.
2. **Guest Card**: Instant single-API lookup by guest name or phone number. Displays visit count, last visit date, top 3 favorite dishes, dietary restrictions & allergies (highlighted in bold red), and staff notes with a quick-add note box.
3. **Specials Engine**: Algorithmic next-day specials scoring based on 7-day sales volume, profit margin, recent trend, and freshness penalties. Provides plain-English business rationales. Managers can Approve, Reject, or Swap suggestions.
4. **Operations Dashboard**: Live daily revenue, order volume, top 5 and bottom 5 sellers with CSS bar graphs. When viewed as Owner, confidential dish costs, gross profit, and margin percentages are unlocked.

---

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLite (pure `sqlite3`, no ORM), Uvicorn.
- **Frontend**: Plain HTML5, Vanilla JavaScript, Tailwind CSS (via CDN).
- **Architecture**: No React, no Node.js, no npm, no build step. Designed to run smoothly on low-RAM phones.
- **PWA**: Installable web app with `manifest.json`, standalone display, and an offline static shell service worker (`sw.js`). API calls (`/api/*`) are strictly never cached.

---

## How to Run Locally on Windows

### Prerequisites
- Python 3.11 installed and added to PATH.

### Step-by-Step Instructions

1. **Open PowerShell** and navigate to your project folder:
   ```powershell
   cd c:\Users\sushi\OneDrive\Attachments\Desktop\hospitality
   ```

2. **Create a virtual environment** (if not already created):
   ```powershell
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   *(If you get a script execution policy error, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

4. **Install the dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

5. **Start the local server**:
   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```

6. **Open in your browser**:
   Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000) (or `http://localhost:8000`).

---

## Database & Auto-Seeding

The app uses a lightweight SQLite database (`restaurant.db`).

- **Automatic Seeding on First Boot**:  
  When the application starts, it creates the database tables from `schema.sql` if they don't exist. If the database has no menu items (e.g. fresh installation or cloud deploy), it **automatically seeds**:
  - 34 authentic South Indian menu items across 5 categories in Indian Rupees (₹)
  - 8 dining tables (T1 to T8)
  - 40 sample guests (15 with realistic dietary notes/allergies)
  - ~2,000 closed orders spanning the past 30 days
  - Scored specials with top 3 approved for both today and tomorrow
  - Elaneer (Tender Coconut) marked unavailable for demo testing
- **Manual Reseed**:  
  To reset the database at any time, delete `restaurant.db` or run:
  ```powershell
  python -m app.seed
  ```

---

## Role Switcher & Permissions

Role-based access control is simulated via a top-bar dropdown. The selected role is saved in `localStorage` and sent on every request via the `X-Role` HTTP header:

| Role | Permissions |
| :--- | :--- |
| **Waiter** | Order Entry, Guest Card lookup & notes, view today's approved specials (read-only). |
| **Manager** | All Waiter features + Generate/Approve/Swap tomorrow's specials, view daily sales & volume dashboard. |
| **Owner** | All Manager features + view unit costs, gross dollar profit, and profit margin percentages. |

*If a user attempts an unauthorized action (e.g., Waiter attempting to generate specials), the API immediately returns `403 Forbidden`.*

---

## Known Limits (Demo Scope)

1. **Simulated Authentication**: Staff roles are chosen via the UI dropdown and communicated via `X-Role` headers. There are no passwords or JWT tokens because this is a rapid internal demo without guest-facing access.
2. **Ephemeral Disk on Free Hosting**: Render's free tier spins down servers after inactivity and resets disk state on new containers. Our automatic startup seeder handles this by repopulating data on boot.
3. **Single-Node SQLite**: SQLite is embedded and single-file. It is lightweight and fast for a local small restaurant, but not intended for horizontally scaled, multi-server clusters.


## To access the live website click on https://hospitality-platform1.onrender.com/
