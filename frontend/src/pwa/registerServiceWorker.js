export function register() {
  if (import.meta.env.PROD && 'serviceWorker' in navigator) {
    // The URL constructor is available in all browsers that support SW.
    const publicUrl = new URL(import.meta.env.BASE_URL, window.location.href)
    if (publicUrl.origin !== window.location.origin) {
      // Our service worker won't work if PUBLIC_URL is on a different origin
      // from what our page is served on. This might happen if a CDN is used to
      // serve assets; see https://github.com/facebook/create-react-app/issues/2374
      return
    }

    window.addEventListener('load', () => {
      const swUrl = `${import.meta.env.BASE_URL}sw.js`

      registerValidSW(swUrl)
    })
  }
}

function registerValidSW(swUrl) {
  navigator.serviceWorker
    .register(swUrl)
    .then((registration) => {
      // [AG-CLEANUP] console.log('Service Worker registered with scope:', registration.scope);

      // التحقق من وجود تحديثات للـ Service Worker
      registration.addEventListener('updatefound', () => {
        const installingWorker = registration.installing

        installingWorker.addEventListener('statechange', () => {
          if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // تم العثور على تحديث جديد
            // [AG-CLEANUP] console.log('New content is available; please refresh.');

            // إظهار إشعار للمستخدم بوجود تحديث
            if (confirm('يوجد تحديث جديد للتطبيق. هل ترغب في التحديث الآن؟')) {
              window.location.reload()
            }
          }
        })
      })

      // مراقبة حالة الاتصال
      window.addEventListener('online', () => {
        // [AG-CLEANUP] console.log('App is now online');
        // إرسال حدث مزامنة للـ Service Worker
        if (registration.active) {
          registration.active.postMessage({ type: 'SYNC_NOW' })
        }
      })

      window.addEventListener('offline', () => {
        // [AG-CLEANUP] console.log('App is now offline');
      })
    })
    .catch((error) => {
      console.error('Error during service worker registration:', error)
    })
}

export function unregister() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.unregister()
      })
      .catch((error) => {
        console.error(error.message)
      })
  }
}

// دالة لمزامنة البيانات يدوياً
export function syncData() {
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ type: 'SYNC_NOW' })
  }
}

// دالة للتحقق من حالة الاتصال
export function isOnline() {
  return navigator.onLine
}

// دالة لإضافة مستمع لأحداث الاتصال
export function addConnectionListener(callback) {
  window.addEventListener('online', callback)
  window.addEventListener('offline', callback)

  // إرجاع دالة لإزالة المستمع
  return () => {
    window.removeEventListener('online', callback)
    window.removeEventListener('offline', callback)
  }
}
