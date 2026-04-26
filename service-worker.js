
const CACHE_NAME = "saradud-v2.0";
const OFFLINE_URLS = ["/frontend/index.html","/offline.html","/manifest.webmanifest"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(OFFLINE_URLS)));
});
self.addEventListener("fetch", (e) => {
  e.respondWith(
    caches.match(e.request).then((r) => r || fetch(e.request).catch(()=>caches.match("/offline.html")))
  );
});
