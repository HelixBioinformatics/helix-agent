/** Whitelist model request fields; never store headers, auth or input content. */
import fs from "node:fs/promises"

export default async () => {
  const output = process.env.HELIX_PILOT_SETTINGS_OUTPUT
  if (!output) throw new Error("Operator must select the settings evidence file")
  const originalFetch = globalThis.fetch
  globalThis.fetch = (async (input: Parameters<typeof fetch>[0], init?: Parameters<typeof fetch>[1]) => {
    const url = input instanceof Request ? new URL(input.url) : new URL(String(input))
    if (url.hostname === "chatgpt.com" && url.pathname.endsWith("/responses") && typeof init?.body === "string") {
      const body = JSON.parse(init.body)
      await fs.appendFile(output, JSON.stringify({
        stage: "outbound-request",
        at: new Date().toISOString(),
        endpoint: url.origin + url.pathname,
        model: body.model ?? null,
        reasoningEffort: body.reasoning?.effort ?? null,
        serviceTier: body.service_tier ?? null,
        maximumOutputTokens: body.max_output_tokens ?? null,
        store: body.store ?? null,
        stream: body.stream ?? null,
      }) + "\n", { mode: 0o600 })
    }
    return originalFetch(input, init)
  }) as typeof fetch
  return {
    "chat.params": async (input: { agent: string; model: { id: string; providerID: string } }, outputParams: { maxOutputTokens?: number; options?: Record<string, unknown> }) => {
      await fs.appendFile(output, JSON.stringify({
        stage: "configured-parameters",
        at: new Date().toISOString(),
        agent: input.agent,
        model: input.model.id,
        provider: input.model.providerID,
        maximumOutputTokens: outputParams.maxOutputTokens ?? null,
        reasoningEffort: outputParams.options?.reasoningEffort ?? null,
        serviceTier: outputParams.options?.serviceTier ?? null,
      }) + "\n", { mode: 0o600 })
    },
  }
}
