import { useState, useCallback } from 'react'
import axios from 'axios'
import { checkGuardrails } from '../utils/guardrails'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL

/**
 * useChat — manages all chat state.
 *
 * State shape:
 * {
 *   messages: [{ role: "user"|"assistant", content: string, meta: null|{...} }],
 *   loading: boolean,
 *   error: string|null
 * }
 */
export function useChat() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const appendMessage = useCallback((msg) => {
    setMessages((prev) => [...prev, msg])
  }, [])

  const sendMessage = useCallback(
    async (query) => {
      const trimmed = query.trim()
      if (!trimmed) return

      // Clear previous error
      setError(null)

      // Append user message
      appendMessage({ role: 'user', content: trimmed, meta: null })

      // ── Guardrail check ──────────────────────────────────────────────────
      const guardrailMessage = checkGuardrails(trimmed)
      if (guardrailMessage) {
        appendMessage({
          role: 'assistant',
          content: guardrailMessage,
          meta: null,
        })
        return
      }

      // ── API call ─────────────────────────────────────────────────────────
      setLoading(true)
      try {
        const response = await axios.post(`${BACKEND_URL}/chat`, {
          query: trimmed,
        })

        const data = response.data
        appendMessage({
          role: 'assistant',
          content: data.answer,
          meta: {
            confidence: data.confidence,
            related_questions: data.related_questions || [],
            chunks: data.chunks || [],
          },
        })
      } catch (err) {
        const errorMsg =
          err?.response?.data?.detail ||
          err?.message ||
          'Something went wrong. Please try again.'
        setError(errorMsg)
        appendMessage({
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          meta: null,
        })
      } finally {
        setLoading(false)
      }
    },
    [appendMessage]
  )

  return { messages, loading, error, sendMessage }
}
