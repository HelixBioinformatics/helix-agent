import { useTheme } from "../context/theme"
import { MARK_INNER, MARK_OUTER } from "../logo"

/** Decorative identity only; never use this alphabet to encode tool outcomes. */
export function identityAlphabet(ascii = process.env.HELIX_ASCII === "1" || process.env.TERM === "dumb") {
  return ascii
    ? { outer: "*", inner: "o", rung: "-", point: "." }
    : { outer: MARK_OUTER, inner: MARK_INNER, rung: "─", point: "." }
}

export const TRANSCRIPT_INSET = 2

/** Only the presentation we introduce opts into plain terminal rules. */
export function identityBorder() {
  if (identityAlphabet().outer !== "*") return undefined
  return {
    topLeft: "+",
    topRight: "+",
    bottomLeft: "+",
    bottomRight: "+",
    horizontal: "-",
    vertical: "|",
    bottomT: "+",
    topT: "+",
    cross: "+",
    leftT: "+",
    rightT: "+",
  }
}

/** A small signature that fits in the session's existing chrome. */
export function Identity() {
  const { theme } = useTheme()
  return (
    <text selectable={false} flexShrink={0} fg={theme.text}>
      <b>
        helix<span style={{ fg: theme.primary }}>.</span>
      </b>
    </text>
  )
}
