/**
 * Simple Service Worker for Hospitality Management Platform
 * Caches static shell assets. Explicitly NEVER caches /api requests.
 */
const CACHE_NAME = "dakshin-v4";
const STATIC_ASSETS = [
  "/static/index.html",
  "/static/guest.html",
  "/static/specials.html",
  "/static/dashboard.html",
  "/static/app.js",
  "/static/manifest.json",
  "/static/icon.svg",
  "/static/icon-192.png",
  "/static/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // CRITICAL RULE: NEVER cache any API calls
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Network first with cache fallback for static assets
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
