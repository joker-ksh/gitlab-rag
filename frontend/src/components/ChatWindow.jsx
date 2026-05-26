import React, { useState, useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import RelatedQuestions from './RelatedQuestions'
import './ChatWindow.css'

const STARTER_QUESTIONS = [
  "What are GitLab's core values?",
  "How does GitLab approach remote work?",
  "Why does GitLab prefer async communication?",
  "What is the GitLab hiring process?",
]

export default function ChatWindow({ messages, loading, error, onSendMessage }) {
  const [inputValue, setInputValue] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = () => {
    const trimmed = inputValue.trim()
    if (!trimmed || loading) return
    onSendMessage(trimmed)
    setInputValue('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const lastAssistantIndex = messages
    .map((m, i) => (m.role === 'assistant' ? i : -1))
    .filter((i) => i !== -1)
    .at(-1)

  return (
    <section className="chat-window">
      {/* Page title */}
      <div className="chat-window__page-title">
        <h1>Handbook AI Assistant</h1>
        <p>Ask anything about the GitLab handbook — values, culture, processes, and more.</p>
      </div>
      <hr className="chat-window__divider" />

      {/* Error banner */}
      {error && (
        <div className="chat-window__error" role="alert">⚠ {error}</div>
      )}

      {/* Messages */}
      <div className="chat-window__messages">
        {messages.length === 0 && (
          <div className="chat-window__welcome">
            <div className="chat-window__welcome-icon">🦊</div>
            <h2>Ask the GitLab Handbook</h2>
            <p>
              This assistant searches the GitLab handbook using semantic + keyword retrieval
              and answers only from what's in the handbook.
            </p>
            <div className="chat-window__welcome-chips">
              {STARTER_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  className="chat-window__welcome-chip"
                  onClick={() => onSendMessage(q)}
                  type="button"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <React.Fragment key={i}>
            <MessageBubble message={msg} />
            {msg.role === 'assistant' &&
              i === lastAssistantIndex &&
              msg.meta?.related_questions?.length > 0 && (
                <RelatedQuestions
                  questions={msg.meta.related_questions}
                  onSelect={onSendMessage}
                />
              )}
          </React.Fragment>
        ))}

        {loading && (
          <div className="chat-window__typing" aria-label="Assistant is typing">
            <span /><span /><span />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-window__input-area">
        <div className="chat-window__composer">
          <textarea
            className="chat-window__input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the GitLab handbook..."
            rows={2}
            disabled={loading}
            aria-label="Chat input"
          />
          <div className="chat-window__composer-toolbar">
            <span className="chat-window__input-hint">
              <kbd>Enter</kbd> to send &nbsp;·&nbsp; <kbd>Shift+Enter</kbd> for new line
            </span>
            <button
              className="chat-window__send-btn"
              onClick={handleSend}
              disabled={loading || !inputValue.trim()}
              aria-label="Send message"
              type="button"
            >
              {/* Paper plane icon */}
              <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
              Send
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
