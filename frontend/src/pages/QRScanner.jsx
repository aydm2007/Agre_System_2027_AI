import { useState, useEffect, useRef } from 'react'
import { Html5Qrcode } from 'html5-qrcode'
import {
  QrCode as QrCodeIcon,
  CheckCircle as CheckCircleIcon,
  X as XMarkIcon,
  Video as VideoCameraIcon,
} from 'lucide-react'
import { api, Farms, Locations } from '../api/client'
import { useToast } from '../components/ToastProvider'
import { useTranslation } from 'react-i18next'
import { v4 as uuidv4 } from 'uuid'

export default function QRScanner() {
  // eslint-disable-next-line no-unused-vars
  const { t } = useTranslation()
  const addToast = useToast()

  const [farms, setFarms] = useState([])
  const [locations, setLocations] = useState([])
  const [selectedFarm, setSelectedFarm] = useState('')
  const [selectedLocation, setSelectedLocation] = useState('')

  const [scanResult, setScanResult] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [scannerActive, setScannerActive] = useState(false)

  const [amount, setAmount] = useState('')
  const [itemAction, setItemAction] = useState('consume')
  const [note, setNote] = useState('')

  const scannerRef = useRef(null)

  useEffect(() => {
    // Load farms on mount
    const loadFarms = async () => {
      try {
        const res = await Farms.list()
        setFarms(res.data?.results || res.data || [])
      } catch (err) {
        addToast('فشل تحميل المزارع', 'error')
      }
    }
    loadFarms()
  }, [addToast])

  useEffect(() => {
    const loadLocations = async () => {
      if (!selectedFarm) return setLocations([])
      try {
        const res = await Locations.list({ farm_id: selectedFarm })
        setLocations(res.data?.results || res.data || [])
      } catch (err) {
        addToast('فشل تحميل المواقع', 'error')
      }
    }
    loadLocations()
  }, [selectedFarm, addToast])

  const startScanner = () => {
    if (!selectedFarm) {
      addToast('يجب اختيار المزرعة أولاً', 'error')
      return
    }

    setScannerActive(true)
    setScanResult(null)

    setTimeout(() => {
      const html5QrCode = new Html5Qrcode('qr-reader')
      scannerRef.current = html5QrCode

      const qrCodeSuccessCallback = async (decodedText) => {
        // Pause scanning while resolving
        html5QrCode.pause(true)
        await resolveQRCode(decodedText)
      }

      const config = { fps: 10, qrbox: { width: 250, height: 250 } }
      html5QrCode
        .start({ facingMode: 'environment' }, config, qrCodeSuccessCallback)
        .catch((err) => {
          console.error('Error starting camera', err)
          addToast('تعذر الوصول للكاميرا', 'error')
          setScannerActive(false)
        })
    }, 100) // slight delay to mount div
  }

  const stopScanner = () => {
    if (scannerRef.current) {
      scannerRef.current
        .stop()
        .then(() => {
          scannerRef.current.clear()
          scannerRef.current = null
          setScannerActive(false)
        })
        .catch((err) => {
          console.error('Error stopping scanner', err)
        })
    } else {
      setScannerActive(false)
    }
  }

  const resolveQRCode = async (qrString) => {
    setIsProcessing(true)
    try {
      const response = await api.post('/qr-operations/resolve/', {
        qr_string: qrString,
        farm_id: selectedFarm,
      })
      setScanResult({ ...response.data, rawQr: qrString })
      addToast('تم المسح بنجاح، أكمل البيانات.', 'success')
    } catch (error) {
      addToast(error.response?.data?.error || 'كود QR غير صالح', 'error')
      if (scannerRef.current) {
        scannerRef.current.resume()
      }
    } finally {
      setIsProcessing(false)
    }
  }

  const handleExecute = async () => {
    if (scanResult.type === 'item' && (!amount || amount <= 0)) {
      addToast('يرجى إدخال كمية صحيحة', 'error')
      return
    }

    setIsProcessing(true)
    try {
      // Offline/Idempotent Guard
      const idempotencyKey = uuidv4()

      const payload = {
        qr_string: scanResult.rawQr,
        action: scanResult.type === 'item' ? itemAction : 'attendance',
        farm_id: selectedFarm,
        location_id: selectedLocation || undefined,
        note: note,
      }

      if (scanResult.type === 'item') {
        payload.amount = amount
      }

      const res = await api.post('/qr-operations/execute/', payload, {
        headers: {
          'X-Idempotency-Key': idempotencyKey,
        },
      })

      addToast(res.data.message || 'تم تنفيذ الحركة بنجاح', 'success')

      // Cleanup for next scan
      setScanResult(null)
      setAmount('')
      setNote('')
      stopScanner()
    } catch (error) {
      addToast(error.response?.data?.error || 'حدث خطأ أثناء التنفيذ', 'error')
    } finally {
      setIsProcessing(false)
    }
  }

  const resetScan = () => {
    setScanResult(null)
    setAmount('')
    setNote('')
    if (scannerRef.current) {
      scannerRef.current.resume()
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (scannerRef.current && scannerRef.current.isScanning) {
        scannerRef.current.stop().catch(console.error)
      }
    }
  }, [])

  return (
    <div className="p-4 sm:p-6 max-w-lg mx-auto pb-24">
      <div className="text-center mb-6">
        <QrCodeIcon className="mx-auto h-10 w-10 text-indigo-500 mb-2" />
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          الماسح الميداني (QR Scanner)
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          تتبع المخزون وتسجيل حضور العمال فورياً بدون أخطاء إدخال يدوي.
        </p>
      </div>

      {!scanResult && !scannerActive && (
        <div className="bg-white dark:bg-slate-800 shadow rounded-xl p-4 sm:p-6 mb-6 ring-1 ring-gray-900/5 dark:ring-white/10">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            المزرعة الحالية *
          </label>
          <select
            value={selectedFarm}
            onChange={(e) => setSelectedFarm(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm dark:bg-slate-900 dark:border-slate-700 dark:text-white"
          >
            <option value="">-- اختر المزرعة --</option>
            {farms.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>

          <button
            onClick={startScanner}
            disabled={!selectedFarm}
            className={`mt-6 w-full flex items-center justify-center gap-2 rounded-md px-4 py-3 text-sm font-bold text-white shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600
              ${!selectedFarm ? 'bg-indigo-300 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500'}`}
          >
            <VideoCameraIcon className="h-5 w-5" />
            فتح الكاميرا للمسح
          </button>
        </div>
      )}

      {scannerActive && !scanResult && (
        <div className="bg-black rounded-xl overflow-hidden shadow-xl ring-1 ring-gray-900/10 mb-6">
          {/* The div where html5-qrcode will render the camera view */}
          <div id="qr-reader" className="w-full"></div>

          <div className="p-4 text-center">
            <button
              onClick={stopScanner}
              className="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600"
            >
              إغلاق الماسح
            </button>
          </div>
        </div>
      )}

      {scanResult && (
        <div className="bg-white dark:bg-slate-800 shadow rounded-xl p-4 sm:p-6 ring-1 ring-green-600/30">
          <div className="flex border-b border-gray-100 dark:border-slate-700 pb-4 mb-4 justify-between items-start">
            <div>
              <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20 mb-2">
                <CheckCircleIcon className="h-3 w-3" /> تم التعرف بنجاح
              </span>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">{scanResult.name}</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                النوع: {scanResult.type === 'item' ? 'مادة/صنف' : 'موظف/عامل'}
              </p>
            </div>
            <button onClick={resetScan} className="text-gray-400 hover:text-gray-600 p-1">
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {/* If the scanned entity is an ITEM (Stock) */}
          {scanResult.type === 'item' && (
            <div className="space-y-4">
              <div>
                <p className="text-xs text-gray-500">المخزون الحالي في المزرعة المحددة:</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white" dir="ltr">
                  {scanResult.current_qty} {scanResult.uom}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    نوع الحركة
                  </label>
                  <select
                    value={itemAction}
                    onChange={(e) => setItemAction(e.target.value)}
                    className="mt-1 w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm dark:bg-slate-900 dark:border-slate-700 dark:text-white"
                  >
                    <option value="consume">صرف (استهلاك)</option>
                    <option value="add">إضافة (استلام)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    الكمية ({scanResult.uom}) *
                  </label>
                  <input
                    type="number"
                    step="any"
                    min="0.01"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className="mt-1 w-full rounded-md border-gray-300 py-2 px-3 text-base focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm dark:bg-slate-900 dark:border-slate-700 dark:text-white"
                    required
                  />
                </div>
              </div>

              {locations.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    الموقع (اختياري)
                  </label>
                  <select
                    value={selectedLocation}
                    onChange={(e) => setSelectedLocation(e.target.value)}
                    className="mt-1 w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm dark:bg-slate-900 dark:border-slate-700 dark:text-white"
                  >
                    <option value="">-- بدون موقع محدد --</option>
                    {locations.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}

          {/* If the scanned entity is an EMPLOYEE (Attendance) */}
          {scanResult.type === 'employee' && (
            <div className="space-y-4">
              <div className="bg-indigo-50 dark:bg-indigo-900/20 p-3 rounded-md text-sm text-indigo-800 dark:text-indigo-300 font-medium text-center">
                سيتم تسجيل حضور نظام الصرة (1.0 يوم كامل) لهذا العامل اليوم.
              </div>
            </div>
          )}

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              ملاحظات (اختياري)
            </label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="دوّن أي ملاحظة إضافية..."
              className="w-full rounded-md border-gray-300 py-2 px-3 text-base focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm dark:bg-slate-900 dark:border-slate-700 dark:text-white"
            />
          </div>

          <button
            onClick={handleExecute}
            disabled={isProcessing}
            className={`mt-6 w-full flex items-center justify-center gap-2 rounded-md px-4 py-3 text-sm font-bold text-white shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 
              ${isProcessing ? 'bg-indigo-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500 focus-visible:outline-indigo-600'}`}
          >
            {isProcessing ? 'جاري التنفيذ والتشفير...' : 'تأكيد العملية'}
          </button>
        </div>
      )}
    </div>
  )
}
