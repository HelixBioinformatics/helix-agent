import type { AssistantMessage } from "@helix/sdk/v2"
import type { TuiPlugin, TuiPluginApi } from "@helix/plugin/tui"
import type { BuiltinTuiPlugin } from "../builtins"
import { createMemo } from "solid-js"
import { identityBorder } from "../../ui/identity"

const id = "internal:sidebar-context"

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
})

function View(props: { api: TuiPluginApi; session_id: string }) {
  const theme = () => props.api.theme.current
  const msg = createMemo(() => props.api.state.session.messages(props.session_id))
  const session = createMemo(() => props.api.state.session.get(props.session_id))
  const cost = createMemo(() => session()?.cost ?? 0)

  const state = createMemo(() => {
    const last = msg().findLast((item): item is AssistantMessage => item.role === "assistant" && item.tokens.output > 0)
    if (!last) {
      return {
        tokens: 0,
        percent: null,
      }
    }

    const tokens =
      last.tokens.input + last.tokens.output + last.tokens.reasoning + last.tokens.cache.read + last.tokens.cache.write
    const model = props.api.state.provider.find((item) => item.id === last.providerID)?.models[last.modelID]
    return {
      tokens,
      percent: model?.limit.context ? Math.round((tokens / model.limit.context) * 100) : null,
    }
  })

  return (
    <box border={["top"]} borderColor={theme().borderSubtle} customBorderChars={identityBorder()}>
      <text fg={theme().text}>
        <b>Context</b>
      </text>
      <box flexDirection="row" gap={1}>
        <text width={12} fg={theme().text}>
          {state().tokens.toLocaleString().padStart(12)}
        </text>
        <text fg={theme().textMuted}>tokens</text>
      </box>
      <box flexDirection="row" gap={1}>
        <text width={12} fg={theme().text}>
          {`${state().percent ?? 0}%`.padStart(12)}
        </text>
        <text fg={theme().textMuted}>used</text>
      </box>
      <box flexDirection="row" gap={1}>
        <text width={12} fg={theme().text}>
          {money.format(cost()).padStart(12)}
        </text>
        <text fg={theme().textMuted}>spent</text>
      </box>
    </box>
  )
}

const tui: TuiPlugin = async (api) => {
  api.slots.register({
    order: 100,
    slots: {
      sidebar_content(_ctx, props) {
        return <View api={api} session_id={props.session_id} />
      },
    },
  })
}

const plugin: BuiltinTuiPlugin = {
  id,
  tui,
}

export default plugin
