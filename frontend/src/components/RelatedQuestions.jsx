import React from 'react'
import './RelatedQuestions.css'

export default function RelatedQuestions({ questions, onSelect }) {
  if (!questions || questions.length === 0) return null

  return (
    <div className="related-questions">
      <p className="related-questions__label">You might also want to ask</p>
      <div className="related-questions__chips">
        {questions.map((q, i) => (
          <button
            key={i}
            className="related-questions__chip"
            onClick={() => onSelect(q)}
            type="button"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
