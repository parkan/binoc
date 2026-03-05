# Per-Outputter Config and Significance as an Outputter Concern

**Date:** 2026-03-09
**Status:** Decided (implemented)

## Problem

The original design placed significance classification config in a flat `output.significance` section of the dataset config:

```yaml
output:
  significance:
    ministerial:
      - binoc.column-reorder
    substantive:
      - binoc.column-addition
```

This had two problems:

1. **It "knew too much" for the config layer.** The significance mapping is inherently format-specific — it only matters to outputters that render human-readable changelogs (Markdown, potentially HTML). JSON migration output doesn't use it. A CI-check outputter might want a completely different mapping. Putting it at the top level of `output` implied it was a universal output concern.

2. **No mechanism for outputter-specific config.** The `Outputter` trait's `render` method received a monolithic `OutputConfig` struct. Every new outputter-specific knob would require modifying this shared struct — the opposite of a plugin architecture. A future HTML outputter wanting a `theme` setting, or a CI outputter wanting a `fail_on` list, would all crowd into the same type.

## Options Considered

### A: Significance as a transformer (rejected)

Make significance classification a transformer that annotates IR nodes with a `significance` field. Outputters read annotations.

Rejected because it pushes an outputter concern into the IR phase, violating the design principle that the IR carries factual tags and the outputter interprets them. It would bake a significance judgment into the migration JSON, which is supposed to be format-agnostic and judgment-free. Different outputters couldn't apply different significance mappings to the same migration.

### B: Per-outputter config sections (chosen)

The `output` section becomes a map from outputter names to outputter-specific config objects. Each outputter defines its own config schema and defaults.

```yaml
output:
  markdown:
    significance:
      ministerial:
        - binoc.column-reorder
      substantive:
        - binoc.column-addition
```

The `Outputter::render` method receives a `serde_json::Value` (the outputter's own config section) instead of a monolithic `OutputConfig`. The outputter deserializes it into its own config type with `#[serde(default)]` for missing fields.

## Decision

Option B. The implementation:

- **`OutputConfig`** is now a struct wrapping `BTreeMap<String, serde_json::Value>` with `#[serde(flatten)]`. `get_for_outputter(name)` resolves both short names (`"markdown"`) and qualified names (`"binoc.markdown"`).

- **`Outputter::render`** receives `&serde_json::Value` — the outputter's own config section, or an empty object if absent. Outputters deserialize this into their own config types and apply their own defaults.

- **`MarkdownOutputterConfig`** is a new public type in `binoc-core::output` with a `significance: BTreeMap<String, Vec<String>>` field. Default significance (the standard ministerial/substantive mapping) lives here, not in the global config.

- **The migration IR is unchanged.** Tags remain factual; significance classification remains an outputter concern. Different outputters can apply different significance mappings to the same migration.

## Consequences

- The same pattern naturally extends to future outputter-specific config (HTML themes, CI failure rules, etc.) without modifying shared types.
- Third-party outputters define their own config schemas — no coordination with core needed.
- The existing config format changes: `output.significance.*` becomes `output.markdown.significance.*`. This is a breaking change, acceptable since the project is pre-release.
- Per-plugin config for comparators and transformers is not yet implemented but could follow the same pattern (`comparator_config`, `transformer_config` sections) if needed.
