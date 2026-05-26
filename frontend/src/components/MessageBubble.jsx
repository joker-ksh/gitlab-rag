import React from 'react'
import ReactMarkdown from 'react-markdown'
import './MessageBubble.css'

export default function MessageBubble({ message }) {
  const { role, content } = message
  const isUser = role === 'user'

  return (
    <div className={`message-bubble message-bubble--${role}`}>
      <div className="message-bubble__wrapper">
        <span className="message-bubble__role">
          {isUser ? 'You' : '🦊 Handbook AI'}
        </span>
        <div className="message-bubble__content">
          {isUser
            ? <span>{content}</span>
            : <ReactMarkdown>{content}</ReactMarkdown>
          }
        </div>
      </div>
    </div>
  )
}
