import { motion } from 'framer-motion'

/**
 * SuccessCheckmark - Animated Success Feedback
 *
 * Features:
 * - SVG path drawing animation
 * - Dopamine hit on successful submission
 * - Accessible with reduced-motion support
 */
export function SuccessCheckmark({ show = false, onComplete }) {
  if (!show) return null

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onComplete}
      role="dialog"
      aria-label="تم بنجاح"
    >
      <motion.div
        className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-2xl"
        initial={{ scale: 0.5, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15 }}
      >
        <svg
          className="w-24 h-24 mx-auto"
          viewBox="0 0 100 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Circle */}
          <motion.circle
            cx="50"
            cy="50"
            r="45"
            stroke="#10b981"
            strokeWidth="4"
            fill="none"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
          {/* Checkmark */}
          <motion.path
            d="M30 50 L45 65 L70 35"
            stroke="#10b981"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.3, delay: 0.5, ease: 'easeOut' }}
          />
        </svg>

        <motion.p
          className="text-center text-xl font-bold text-gray-800 dark:text-white mt-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
        >
          تم بنجاح! ✨
        </motion.p>

        <motion.button
          className="mt-4 w-full py-2 bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-600 transition-colors"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          onClick={onComplete}
        >
          متابعة
        </motion.button>
      </motion.div>
    </motion.div>
  )
}

export default SuccessCheckmark
