import React from 'react'
import './ConfidenceBadge.css'

const CONFIG = {
  high:   { icon: '✓', label: 'High Confidence' },
  medium: { icon: '~', label: 'Medium Confidence' },
  low:    { icon: '!', label: 'Low Confidence' },
  none:   { icon: '✕', label: 'No Match Found' },
}

export default function ConfidenceBadge({ confidence }) {
  if (!confidence) return null
  const { level, message } = confidence
  const cfg = CONFIG[level] || CONFIG.none

  return (
    <div className={`confidence-badge confidence-badge--${level}`}>
      <span className="confidence-badge__label">
        {cfg.icon} {cfg.label}
      </span>
      {message && <p className="confidence-badge__message">{message}</p>}
    </div>
  )
}
