# Selection-grounded defense explanations

In **論文精修**, select a sentence, concept or table-cell text to receive a
contextual defense explanation. The automatic action is debounced and can be
disabled; **答辯解釋** also works manually. Each displayed equation has a direct
explanation action, including formulas whose readable source is LaTeX only.

The explanation covers meaning, role in the manuscript, symbols/units,
illustrative numerical calculations, an everyday analogy, assumptions and
limits, a short oral-defense script and likely follow-up questions. Numerical
examples are explicitly teaching assumptions, not empirical findings of the
paper. Undefined terms and missing parameters are identified rather than
invented. Manuscript content is research input, not agent instructions.

## Existing infrastructure

`POST /api/research/projects/{project}/files/{file}/refinement/defense-explanations`
accepts `selection` and optional `refresh`. Selection includes `block_id`,
`field_name` (`text`, `cell`, or this endpoint's formula-only `latex`), optional
`cell_index`, `start_offset`, `end_offset`, `quote` and
`offset_encoding: "utf16"` for browser coordinates. The server verifies the
selection against the current draft and rejects stale anchors.

It uses the tenant's existing model connection in the fast, non-thinking mode,
with selected and adjacent context prioritized within a bounded prompt.
Completed explanations are pinned to the draft revision and saved in the
existing manuscript conversation history. Repeated identical selections reuse
the current revision's answer. Regeneration is explicit. No schema change,
separate runtime or new model connection is required.

The operation requires existing `research.write`, like manuscript refinement.
Internal capability `research_manuscript_defense_explain` uses the same endpoint.
It never applies text changes to the manuscript. In-flight responses for an old
selection or document do not replace the current explanation.

Verification covers this selection/context/cache/permission path, one browser
sentence-and-formula flow, and a necessary live model/readback check.
