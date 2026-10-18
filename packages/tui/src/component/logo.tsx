import { CliRenderEvents, TextAttributes } from "@opentui/core"
import { useRenderer } from "@opentui/solid"
import { createSignal, For, onCleanup, Show } from "solid-js"
import { useTheme } from "../context/theme"
import { MARK_INNER, MARK_OUTER, mark } from "../logo"
import { identityAlphabet } from "../ui/identity"

export function Logo(props: { compact?: boolean }) {
  const { theme } = useTheme()
  const renderer = useRenderer()
  const alphabet = identityAlphabet()
  const [cell, setCell] = createSignal(renderer.widthMethod === "wcwidth" ? 2 : 1)
  const updateWidth = () => setCell(renderer.widthMethod === "wcwidth" ? 2 : 1)
  renderer.on(CliRenderEvents.CAPABILITIES, updateWidth)
  onCleanup(() => renderer.off(CliRenderEvents.CAPABILITIES, updateWidth))
  const glyph = (char: string) =>
    char === MARK_OUTER ? alphabet.outer : char === MARK_INNER ? alphabet.inner : char === "─" ? alphabet.rung : char

  return (
    <Show
      when={props.compact}
      fallback={
        <box flexDirection="row" gap={3} flexShrink={0}>
          <box width={9 * cell()} flexShrink={0}>
            <For each={mark}>
              {(line) => (
                <box flexDirection="row" height={1}>
                  <For each={Array.from(line.padEnd(9))}>
                    {(char) => (
                      <text
                        width={cell()}
                        selectable={false}
                        fg={char === MARK_OUTER ? theme.primary : char === MARK_INNER ? theme.textMuted : theme.border}
                      >
                        {glyph(char)}
                      </text>
                    )}
                  </For>
                </box>
              )}
            </For>
          </box>
          <box flexGrow={1} minWidth={0} paddingTop={1}>
            <text fg={theme.text} attributes={TextAttributes.BOLD} selectable={false}>
              Helix Agent
            </text>
            <text fg={theme.textMuted} selectable={false}>
              bioinformatics co-scientist
            </text>
          </box>
        </box>
      }
    >
      <text fg={theme.text} selectable={false}>
        <b>Helix Agent</b>
        <span style={{ fg: theme.textMuted }}> / bioinformatics co-scientist</span>
      </text>
    </Show>
  )
}
