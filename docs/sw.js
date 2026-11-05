// Ceaslovnicul service worker: network first, so published updates show on the
// next load; the cache is the offline fallback and fills as pages are read.
const CACHE = "ceaslovnicul-v1";
const YEAR = new Date().getFullYear();
const ASSETS = [
  "./", "./index.html", "./calendar.html", "./manifest.webmanifest", "./css/styles.css", "./css/chi-rho.png",
  "./js/liturgy.js", "./js/app.js",
  "./data/services.json", "./data/hymns.json", "./data/sinaxar.json", "./data/fixed-calendar.json", "./data/psaltire.json", "./data/canon-treime.json",
  `./data/cal-${YEAR}.json`, `./data/cal-${YEAR + 1}.json`,
  ...[1, 2, 3, 4, 5, 6, 7, 8].map((g) => `./data/canon-md-${g}.json`),
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS.map((u) => new Request(u, { cache: "reload" })))));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k.startsWith("ceaslovnicul-") && k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const res = await fetch(new Request(req.url, { cache: "no-cache" }));
      if (res.ok) cache.put(req, res.clone()).catch(() => {});
      return res;
    } catch (err) {
      const hit = await cache.match(req, { ignoreSearch: true });
      if (hit) return hit;
      throw err;
    }
  })());
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    if (all[0]) await all[0].focus();
    else await self.clients.openWindow("./");
  })());
});
