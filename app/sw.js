const CACHE = "stargate-reader-v6";
const SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./feed.json",
  "./manifest.webmanifest",
  "./icon-192.png",
  "./icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || event.request.method !== "GET") return;
  if (url.pathname.endsWith("/feed.json")) {
    event.respondWith(networkFirst(event.request));
    return;
  }
  event.respondWith(cacheFirst(event.request));
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  const copy = response.clone();
  caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => {});
  return response;
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    const copy = response.clone();
    caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => {});
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw new Error("offline");
  }
}
