/**
 * Client-side guardrails — checked before any API call.
 * If a rule matches, its message is returned directly as an assistant reply
 * without hitting the backend.
 */

const GUARDRAIL_RULES = [
  {
    patterns: [/salary|compensation|equity|stock options/i],
    message:
      "Compensation details are not in the public handbook. Please check your offer letter or speak with your People Business Partner.",
  },
  {
    patterns: [/should i quit|should i leave|should i resign/i],
    message:
      "That's a personal decision. I can share GitLab's values and culture to help you think it through — try asking about GitLab's values or remote work culture.",
  },
  {
    patterns: [/your opinion|what do you think|do you believe/i],
    message:
      "I don't form opinions. I can share what the GitLab handbook says — try rephrasing as a question about GitLab's approach or values.",
  },
]

/**
 * Returns a guardrail message string if the query matches a rule, otherwise null.
 * @param {string} query
 * @returns {string|null}
 */
export function checkGuardrails(query) {
  for (const rule of GUARDRAIL_RULES) {
    if (rule.patterns.some((p) => p.test(query))) {
      return rule.message
    }
  }
  return null
}
