import { useState, useEffect, useCallback } from 'react'
import { FarmCrops, Crops } from '../../api/client'
import { X, Search, Loader2, Sprout } from 'lucide-react'
import { useToast } from '../ToastProvider'

export default function FarmCropLinkModal({ farmId, isOpen, onClose, onSuccess }) {
    const toast = useToast()
    const [loading, setLoading] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [crops, setCrops] = useState([])
    const [search, setSearch] = useState('')
    const [selectedCropId, setSelectedCropId] = useState(null)

    const loadGlobalCrops = useCallback(async () => {
        try {
            setLoading(true)
            // Fetch global catalog of crops, bypassing farm scope restriction
            const res = await Crops.list({ global: '1' })
            setCrops(res.data.results || res.data || [])
        } catch (err) {
            console.error(err)
            toast({ title: 'خطأ', message: 'فشل تحميل قائمة المحاصيل' })
        } finally {
            setLoading(false)
        }
    }, [toast])

    useEffect(() => {
        if (isOpen) {
            loadGlobalCrops()
            setSelectedCropId(null)
            setSearch('')
        }
    }, [isOpen, loadGlobalCrops])

    const handleSubmit = async () => {
        if (!selectedCropId) return

        try {
            setSubmitting(true)
            await FarmCrops.create({
                farm: farmId,   // Backend expects 'farm' (ID)
                crop: selectedCropId // Backend expects 'crop' (ID)
            })
            toast({ title: 'نجاح', message: 'تم ربط المحصول بالمزرعة بنجاح', intent: 'success' })
            if (onSuccess) onSuccess()
            onClose()
        } catch (err) {
            console.error(err)
            toast({ title: 'خطأ', message: 'فشل ربط المحصول. ربما هو مضاف بالفعل؟' })
        } finally {
            setSubmitting(false)
        }
    }

    const filteredCrops = crops.filter(c =>
        c.name.toLowerCase().includes(search.toLowerCase())
    )

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-zinc-900 rounded-3xl w-full max-w-lg shadow-2xl border border-white/10 overflow-hidden animate-in zoom-in-95 duration-200">

                {/* Header */}
                <div className="p-6 border-b border-gray-100 dark:border-white/5 flex justify-between items-center bg-gray-50/50 dark:bg-white/[0.02]">
                    <div>
                        <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                            <span className="w-1.5 h-6 bg-emerald-500 rounded-full"></span>
                            إضافة محصول للمزرعة
                        </h3>
                        <p className="text-sm text-gray-500 dark:text-zinc-500 mt-1">
                            اختر محصولاً من القائمة العامة لإضافته لهذه المزرعة
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 bg-gray-100 dark:bg-white/5 hover:bg-rose-500/10 hover:text-rose-500 rounded-xl transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-4">
                    {/* Search */}
                    <div className="relative">
                        <Search className="absolute right-3 top-3 w-5 h-5 text-gray-400" />
                        <input
                            className="w-full bg-gray-100 dark:bg-zinc-800 border-none rounded-xl py-3 pr-10 pl-4 text-gray-900 dark:text-white placeholder:text-gray-500 focus:ring-2 focus:ring-emerald-500/50 transition-all"
                            placeholder="بحث عن محصول..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            autoFocus
                        />
                    </div>

                    <div className="h-64 overflow-y-auto pr-1 space-y-2 custom-scrollbar">
                        {loading ? (
                            <div className="flex flex-col items-center justify-center h-full text-gray-400">
                                <Loader2 className="w-8 h-8 animate-spin mb-2 text-emerald-500" />
                                <p className="text-sm">جاري التحميل...</p>
                            </div>
                        ) : filteredCrops.length === 0 ? (
                            <div className="text-center py-10 text-gray-400 border-2 border-dashed border-gray-200 dark:border-white/5 rounded-xl">
                                لا توجد نتائج مطابقة
                            </div>
                        ) : (
                            filteredCrops.map(crop => (
                                <button
                                    key={crop.id}
                                    onClick={() => setSelectedCropId(crop.id)}
                                    className={`w-full flex items-center justify-between p-4 rounded-xl border transition-all duration-200 group
                    ${selectedCropId === crop.id
                                            ? 'bg-emerald-500/10 border-emerald-500 text-emerald-600 dark:text-emerald-400 shadow-lg shadow-emerald-500/10'
                                            : 'bg-white dark:bg-zinc-800/50 border-gray-200 dark:border-white/5 text-gray-600 dark:text-zinc-400 hover:border-emerald-500/30 hover:bg-gray-50 dark:hover:bg-zinc-800'
                                        }`}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className={`p-2 rounded-lg ${crop.is_perennial ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600' : 'bg-amber-100 dark:bg-amber-900/30 text-amber-600'}`}>
                                            <Sprout className="w-5 h-5" />
                                        </div>
                                        <div className="text-start">
                                            <div className="font-bold">{crop.name}</div>
                                            <div className="text-xs opacity-70">
                                                {crop.is_perennial ? 'أشجار (معمر)' : 'موسمي'}
                                            </div>
                                        </div>
                                    </div>
                                    {selectedCropId === crop.id && (
                                        <div className="w-3 h-3 bg-emerald-500 rounded-full shadow-emerald-500/50 shadow-md animate-in zoom-in"></div>
                                    )}
                                </button>
                            ))
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-gray-100 dark:border-white/5 flex justify-end gap-3 bg-gray-50/50 dark:bg-white/[0.02]">
                    <button
                        onClick={onClose}
                        className="px-6 py-2.5 rounded-xl text-gray-600 dark:text-zinc-400 font-medium hover:bg-gray-100 dark:hover:bg-white/5 transition-colors"
                    >
                        إلغاء
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={!selectedCropId || submitting}
                        className="px-8 py-2.5 rounded-xl bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-500/20 hover:bg-emerald-500 transition-all disabled:opacity-50 disabled:shadow-none flex items-center gap-2"
                    >
                        {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                        {submitting ? 'جاري الإضافة...' : 'إضافة المحصول'}
                    </button>
                </div>
            </div>
        </div>
    )
}
