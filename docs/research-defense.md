# Selection-grounded defense explanations

In **論文精修**, select a sentence, concept or table-cell text to receive a
contextual defense explanation. The automatic action is debounced and can be
disabled; **答辯解釋** also works manually. Each displayed equation has a direct
explanation action, including formulas whose readable source is LaTeX only.

The default explanation gives one plain-language meaning and one small numeric
example from everyday life, with at most one essential limit. It targets
100–180 Chinese characters (at most about 220, excluding equations), without
section headings. **進一步解釋** requests useful symbols, reasoning and limits
within about 450 Chinese characters. Both use Traditional Chinese; illustrative
numbers begin with **假設** and are not presented as the paper's findings.
Undefined terms are identified rather than invented. Equations use standard
LaTeX `\( ... \)` or `\[ ... \]` delimiters and render as mathematics, not code.
Manuscript content is research input, not agent instructions.

## Existing infrastructure

`POST /api/research/projects/{project}/files/{file}/refinement/defense-explanations`
accepts `selection`, optional `refresh`, and `detail: "brief" | "detailed"`
(default `"brief"`; other values return 422). Optional `expected_revision`
rejects changed manuscript context with 409. Selection includes `block_id`,
`field_name` (`text`, `cell`, or this endpoint's formula-only `latex`), optional
`cell_index`, `start_offset`, `end_offset`, `quote` and
`offset_encoding: "utf16"` for browser coordinates. The server verifies the
selection against the current draft and rejects stale anchors.

It uses the tenant's existing model connection in the fast, non-thinking mode,
with selected and adjacent context prioritized within a bounded prompt.
Completed explanations are pinned to the draft revision and saved in the
existing manuscript conversation history. Repeated identical selections reuse
the current revision's answer for the requested detail level. Response and
message metadata include `format_version: 2` and `detail`; the same values are
stored in the selection citation. Earlier answers remain in conversation
history but cannot satisfy this version's cache or default display. The
workspace's `defense_explanations` list exposes both metadata values for
compatible hydration. Regeneration is explicit. No schema change,
separate runtime or new model connection is required.

The operation requires existing `research.write`, like manuscript refinement.
Internal capability `research_manuscript_defense_explain` uses the same endpoint.
It never applies text changes to the manuscript. In-flight responses for an old
selection or document do not replace the current explanation.

The default uses at most 650 output tokens; the detailed option uses at most 1200.
Focused verification covers selection/context/permission safeguards, brief and
detailed prompts, separate caches and preservation of earlier history, plus
the browser's sentence/formula rendering path.
