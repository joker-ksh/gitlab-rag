import React from 'react'
import ConfidenceBadge from './ConfidenceBadge'
import ChunkCard from './ChunkCard'
import './TransparencyPanel.css'

export default function TransparencyPanel({ meta, query }) {
  return (
    <aside className="transparency-panel">
      {/* Sticky header */}
      <div className="transparency-panel__header">
        <p className="transparency-panel__title">On This Query</p>
        {query
          ? <p className="transparency-panel__query">{query}</p>
          : <p className="transparency-panel__query" style={{ color: 'var(--text-muted)', fontWeight: 400, fontStyle: 'italic' }}>
              Ask a question to see retrieval details
            </p>
        }
      </div>

      {/* Body */}
      <div className="transparency-panel__body">
        {!meta ? (
          <div className="transparency-panel__empty">
            <div className="transparency-panel__empty-icon">🔍</div>
            <p>Retrieval details will appear here after you ask a question.</p>
          </div>
        ) : (
          <>
            <ConfidenceBadge confidence={meta.confidence} />

            {meta.chunks && meta.chunks.length > 0 ? (
              <>
                <p className="transparency-panel__section-label">
                  Retrieved Chunks ({meta.chunks.length})
                </p>
                {meta.chunks.map((chunk, i) => (
                  <ChunkCard key={i} chunk={chunk} index={i + 1} />
                ))}
              </>
            ) : (
              <p className="transparency-panel__empty">No chunks retrieved.</p>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
