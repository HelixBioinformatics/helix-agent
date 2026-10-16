export * as ThemeSchema from "./schema"

import { Schema } from "effect"

// The file format of a TUI theme (the ThemeJson type in ./index), published as
// theme.json so editors can check custom themes. test/theme.test.ts fails to
// typecheck when a color is added to one but not the other.

// RGBA.fromHex accepts #rgb, #rgba, #rrggbb and #rrggbbaa.
const HexColor = Schema.String.check(Schema.isPattern(/^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/)).annotate({
  description: "Hex color: #rgb, #rgba, #rrggbb or #rrggbbaa",
})

// Anything not starting with # is looked up in defs, then in theme.
const RefName = Schema.String.check(Schema.isPattern(/^[^#]/)).annotate({
  description: "Name of a color in defs or theme, or transparent / none",
})

const Color = Schema.Union([HexColor, RefName]).annotate({ identifier: "Color" })

const Variant = Schema.Struct({
  dark: Color,
  light: Color,
}).annotate({ identifier: "ColorVariant", description: "Separate colors for dark and light mode" })

const ColorValue = Schema.Union([Color, Variant]).annotate({ identifier: "ColorValue" })

export const Info = Schema.Struct({
  $schema: Schema.optional(Schema.String),
  defs: Schema.optional(Schema.Record(Schema.String, Color)).annotate({
    description: "Named colors that theme values can refer to",
  }),
  theme: Schema.Struct({
    primary: ColorValue,
    secondary: ColorValue,
    accent: ColorValue,
    error: ColorValue,
    warning: ColorValue,
    success: ColorValue,
    info: ColorValue,
    text: ColorValue,
    textMuted: ColorValue,
    selectedListItemText: Schema.optional(ColorValue).annotate({
      description: "Text of the selected list item (default: background)",
    }),
    background: ColorValue,
    backgroundPanel: ColorValue,
    backgroundElement: ColorValue,
    backgroundMenu: Schema.optional(ColorValue).annotate({
      description: "Background of menus (default: backgroundElement)",
    }),
    border: ColorValue,
    borderActive: ColorValue,
    borderSubtle: ColorValue,
    diffAdded: ColorValue,
    diffRemoved: ColorValue,
    diffContext: ColorValue,
    diffHunkHeader: ColorValue,
    diffHighlightAdded: ColorValue,
    diffHighlightRemoved: ColorValue,
    diffAddedBg: ColorValue,
    diffRemovedBg: ColorValue,
    diffContextBg: ColorValue,
    diffLineNumber: ColorValue,
    diffAddedLineNumberBg: ColorValue,
    diffRemovedLineNumberBg: ColorValue,
    markdownText: ColorValue,
    markdownHeading: ColorValue,
    markdownLink: ColorValue,
    markdownLinkText: ColorValue,
    markdownCode: ColorValue,
    markdownBlockQuote: ColorValue,
    markdownEmph: ColorValue,
    markdownStrong: ColorValue,
    markdownHorizontalRule: ColorValue,
    markdownListItem: ColorValue,
    markdownListEnumeration: ColorValue,
    markdownImage: ColorValue,
    markdownImageText: ColorValue,
    markdownCodeBlock: ColorValue,
    syntaxComment: ColorValue,
    syntaxKeyword: ColorValue,
    syntaxFunction: ColorValue,
    syntaxVariable: ColorValue,
    syntaxString: ColorValue,
    syntaxNumber: ColorValue,
    syntaxType: ColorValue,
    syntaxOperator: ColorValue,
    syntaxPunctuation: ColorValue,
    thinkingOpacity: Schema.optional(Schema.Finite.check(Schema.isBetween({ minimum: 0, maximum: 1 }))).annotate({
      description: "Opacity of thinking text (default: 0.6)",
    }),
  }),
}).annotate({ description: "A Helix TUI theme" })
export type Info = Schema.Schema.Type<typeof Info>
