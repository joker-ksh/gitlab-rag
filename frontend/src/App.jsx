import React, { useState } from 'react'
import { useChat } from './hooks/useChat'
import ChatWindow from './components/ChatWindow'
import TransparencyPanel from './components/TransparencyPanel'
import './App.css'

// GitLab fox SVG logo (simplified)
function GitLabLogo() {
  return (
    <svg viewBox="0 0 380 380" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M282.83 170.73l-.27-.69-26.14-68.22a6.81 6.81 0 00-2.69-3.24 7 7 0 00-8 .43 7 7 0 00-2.32 3.52l-17.65 54H154.29l-17.65-54a6.86 6.86 0 00-2.32-3.52 7 7 0 00-8-.43 6.87 6.87 0 00-2.69 3.24L97.44 170l-.26.69a48.54 48.54 0 0016.1 56.1l.09.07.24.17 39.82 29.82 19.7 14.91 12 9.06a8.07 8.07 0 009.19 0l12-9.06 19.7-14.91 40.06-30 .1-.08a48.56 48.56 0 0016.08-56.04z"
        fill="#fff"/>
    </svg>
  )
}

export default function App() {
  const { messages, loading, error, sendMessage } = useChat()
  const [dark, setDark] = useState(false)

  // Apply theme to root
  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  }, [dark])

  // Latest assistant message with meta
  const latestAssistant = [...messages].reverse().find((m) => m.role === 'assistant' && m.meta)
  const latestAssistantMeta = latestAssistant?.meta || null

  // Query that produced the latest answer
  const latestQuery = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'assistant' && messages[i].meta) {
        for (let j = i - 1; j >= 0; j--) {
          if (messages[j].role === 'user') return messages[j].content
        }
      }
    }
    return null
  })()

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="app__header">
        <span className="app__header-logo">
          <GitLabLogo />
          <span className="app__header-title">The GitLab Handbook</span>
        </span>

        <nav className="app__header-nav">
          <a className="app__header-nav-link" href="https://gitlab.com" target="_blank" rel="noreferrer">
            🦊 GitLab
          </a>
          <a className="app__header-nav-link" href="https://handbook.gitlab.com" target="_blank" rel="noreferrer">
            📖 Handbook
          </a>
          <button
            className="app__theme-toggle"
            onClick={() => setDark(d => !d)}
            aria-label="Toggle dark mode"
          >
            {dark ? '☀️ Light' : '🌙 Dark'}
          </button>
        </nav>
      </header>

      {/* ── Breadcrumb ── */}
      <div className="app__breadcrumb">
        <a href="https://handbook.gitlab.com" target="_blank" rel="noreferrer">The Handbook</a>
        <span className="app__breadcrumb-sep">/</span>
        <span>AI Assistant</span>
      </div>

      {/* ── Two-column body ── */}
      <main className="app__body">
        <div className="app__chat-col">
          <ChatWindow
            messages={messages}
            loading={loading}
            error={error}
            onSendMessage={sendMessage}
          />
        </div>
        <div className="app__panel-col">
          <TransparencyPanel meta={latestAssistantMeta} query={latestQuery} />
        </div>
      </main>
    </div>
  )
}
