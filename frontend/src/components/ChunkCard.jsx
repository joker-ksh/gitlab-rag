import React from 'react'
import './ChunkCard.css'

export default function ChunkCard({ chunk, index }) {
  const { description, heading, url, semantic_score, keyword_score, combined_score } = chunk

  return (
    <div className="chunk-card">
      <span className="chunk-card__index">#{index}</span>

      {description && (
        <p className="chunk-card__description">{description}</p>
      )}

      {heading && (
        <p className="chunk-card__section">
          <span className="chunk-card__section-label">Section: </span>{heading}
        </p>
      )}

      <div className="chunk-card__scores">
        <ScoreBar label="Semantic" value={semantic_score} variant="semantic" />
        <ScoreBar label="Keyword"  value={keyword_score}  variant="keyword"  />
        <ScoreBar label="Combined" value={combined_score} variant="combined" />
      </div>

      {url && (
        <a className="chunk-card__source" href={url} target="_blank" rel="noreferrer">
          ↗ {url.replace('https://', '')}
        </a>
      )}
    </div>
  )
}

function ScoreBar({ label, value, variant }) {
  const pct = Math.min(Math.max((value || 0) * 100, 0), 100)
  return (
    <div className="score-bar">
      <span className="score-bar__label">{label}</span>
      <div className="score-bar__track">
        <div
          className={`score-bar__fill score-bar__fill--${variant}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="score-bar__value">{(value || 0).toFixed(2)}</span>
    </div>
  )
}
