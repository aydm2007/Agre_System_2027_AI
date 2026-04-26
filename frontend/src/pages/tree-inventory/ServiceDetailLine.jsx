// Service Detail Line Component
// Extracted from TreeInventory.jsx

import React from 'react'
import { toAsciiDigits } from './utils'

export default function ServiceDetailLine({ label, value, direction = 'auto', className = '' }) {
    if (value == null || value === '') {
        return null
    }

    const wrapperClassName = className && typeof className === 'string' && className.length
        ? className
        : undefined

    const isStringLabel = typeof label === 'string'
    const labelText = isStringLabel ? label.replace(/[:：]\s*$/, '') : label
    const unicodeBidiStyle = direction === 'ltr' ? { unicodeBidi: 'plaintext' } : undefined
    const asciiValue = typeof value === 'string' ? toAsciiDigits(value) : value

    // Render combined text in a single node when label is a plain string
    if (isStringLabel) {
        const combined = `${labelText}: ${asciiValue}`
        return (
            <div className={wrapperClassName} style={unicodeBidiStyle}>
                <span className="inline-block" dir={direction}>{combined}</span>
            </div>
        )
    }

    // Fallback for non-string labels (e.g. React nodes)
    return (
        <div className={wrapperClassName} style={unicodeBidiStyle}>
            {labelText != null && labelText !== '' && <span>{labelText}</span>}
            {labelText != null && labelText !== '' && <span className="mx-1">:</span>}
            <span className="inline-block" dir={direction}>{typeof value === 'string' ? ` ${value}` : value}</span>
            {typeof asciiValue === 'string' && <span className="sr-only">{asciiValue}</span>}
        </div>
    )
}
