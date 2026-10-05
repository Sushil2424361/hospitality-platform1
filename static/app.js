/**
 * Hospitality Management Platform - Shared Frontend Helpers
 * Provides API client with X-Role header, role switcher, navigation,
 * currency formatter, toast notifications, and PWA registration.
 */

// Available staff roles
const ROLES = ["Waiter", "Manager", "Owner"];

/**
 * Get the active staff role from localStorage (defaults to Waiter)
 */
function getRole() {
  const role = localStorage.getItem("staff_role");
  return ROLES.includes(role) ? role : "Waiter";
}

/**
 * Save staff role to localStorage and reload page to reflect permissions
 */
function setRole(newRole) {
  if (ROLES.includes(newRole)) {
    localStorage.setItem("staff_role", newRole);
    // If switching to Waiter while on dashboard, navigate to order screen
    if (newRole === "Waiter" && window.location.pathname.includes("dashboard.html")) {
      window.location.href = "/static/index.html";
      return;
    }
    window.location.reload();
  }
}

/**
 * Formats a number as a USD currency string ($0.00)
 */
function formatMoney(amount) {
  const val = Number(amount) || 0;
  return "$" + val.toFixed(2);
}

/**
 * Displays a non-intrusive floating toast message
 * @param {string} message - Message text
 * @param {'success'|'error'|'info'|'warning'} type - Visual style
 */
function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full px-4 pointer-events-none";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = "pointer-events-auto px-4 py-3 rounded-lg shadow-lg text-sm font-medium flex items-center justify-between transition-all transform duration-200 translate-y-2 opacity-0";

  if (type === "success") {
    toast.className += " bg-emerald-600 text-white";
  } else if (type === "error") {
    toast.className += " bg-rose-600 text-white";
  } else if (type === "warning") {
    toast.className += " bg-amber-500 text-slate-900";
  } else {
    toast.className += " bg-slate-800 text-white";
  }

  toast.innerHTML = `<span>${message}</span><button class="ml-3 font-bold opacity-80 hover:opacity-100">&times;</button>`;
  toast.querySelector("button").onclick = () => toast.remove();

  container.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.remove("translate-y-2", "opacity-0");
  });

  // Auto remove after 3.5 seconds
  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

/**
 * Central API fetch wrapper that automatically attaches the X-Role header
 * and handles HTTP errors with user-friendly messages.
 */
async function api(path, options = {}) {
  const currentRole = getRole();
  const headers = {
    "Content-Type": "application/json",
    "X-Role": currentRole,
    ...(options.headers || {})
  };

  try {
    const response = await fetch(path, { ...options, headers });

    // Handle 403 Forbidden specifically
    if (response.status === 403) {
      showToast(`Access Denied: Action not allowed for role '${currentRole}'.`, "error");
      throw new Error(`Forbidden for role ${currentRole}`);
    }

    let data = null;
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    }

    if (!response.ok) {
      const errorMsg = data && data.detail ? data.detail : `Server error (${response.status})`;
      showToast(errorMsg, "error");
      throw new Error(errorMsg);
    }

    return data;
  } catch (err) {
    if (!err.message.includes("Forbidden")) {
      console.error("API error:", err);
    }
    throw err;
  }
}

/**
 * Injects the responsive header navbar into the #navbar element.
 * Hides links that the current role is not permitted to access.
 * @param {'order'|'guest'|'specials'|'dashboard'} activeTab
 */
function renderNav(activeTab) {
  const navContainer = document.getElementById("navbar");
  if (!navContainer) return;

  const role = getRole();
  const isManagerOrOwner = role === "Manager" || role === "Owner";

  const links = [
    { id: "order", label: "Order Entry", href: "/static/index.html", show: true },
    { id: "guest", label: "Guest Card", href: "/static/guest.html", show: true },
    { id: "specials", label: "Specials", href: "/static/specials.html", show: true },
    { id: "dashboard", label: "Dashboard", href: "/static/dashboard.html", show: isManagerOrOwner }
  ];

  const linksHtml = links
    .filter(link => link.show)
    .map(link => {
      const isActive = link.id === activeTab;
      const activeClasses = isActive
        ? "bg-slate-900 text-white font-semibold shadow-sm"
        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100 font-medium";
      return `
        <a href="${link.href}" class="px-3 py-2 rounded-md text-sm transition-colors whitespace-nowrap min-h-[44px] flex items-center ${activeClasses}">
          ${link.label}
        </a>
      `;
    })
    .join("");

  navContainer.innerHTML = `
    <header class="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16 gap-2">
        <!-- Logo / App Name -->
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-base shadow">
            H
          </div>
          <span class="font-bold text-slate-800 tracking-tight text-base sm:text-lg hidden xs:inline">
            Hospitality
          </span>
        </div>

        <!-- Navigation Links -->
        <nav class="flex items-center gap-1 overflow-x-auto py-1 scrollbar-none">
          ${linksHtml}
        </nav>

        <!-- Role Switcher -->
        <div class="flex items-center gap-2 flex-shrink-0">
          <label for="role-select" class="text-xs font-semibold uppercase tracking-wider text-slate-500 hidden md:inline">
            Role:
          </label>
          <div class="relative">
            <select id="role-select" class="bg-slate-50 hover:bg-slate-100 text-slate-800 text-xs sm:text-sm font-semibold rounded-lg border border-slate-300 px-2.5 py-2 pr-7 min-h-[44px] focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer shadow-sm">
              <option value="Waiter" ${role === "Waiter" ? "selected" : ""}>Waiter</option>
              <option value="Manager" ${role === "Manager" ? "selected" : ""}>Manager</option>
              <option value="Owner" ${role === "Owner" ? "selected" : ""}>Owner</option>
            </select>
          </div>
        </div>
      </div>
    </header>
  `;

  // Attach change listener to role select
  const selectElem = document.getElementById("role-select");
  if (selectElem) {
    selectElem.addEventListener("change", (e) => {
      setRole(e.target.value);
    });
  }
}

// Register service worker for PWA installability
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(err => {
      // SW registration failed, app functions normally without it
      console.debug("Service worker skipped:", err);
    });
  });
}
