# Provenance Tracking and the Extract Chain

**Date:** 2026-03-05
**Status:** Implemented

## Problem

Binoc can tell you *what* changed — "2 rows were added to data.csv" — but not show you the actual data. Users (archivists, data scientists) need to pull out the changed content: which rows were added, what does the text diff look like, what columns were reordered. This is the `extract` verb.

The hard question isn't "how do we read a CSV" — it's **who is responsible for formatting the extracted data?** A node in the migration tree may have been created by one plugin and then rewritten by another. A CSV comparator produces a generic `modify` node with row/column stats. A column reorder transformer then rewrites that node to `kind: "reorder"`. If you ask to extract that node, do you get CSV data (from the comparator) or a column order summary (from the transformer)?

This interacts with container nesting. A file `archive.zip/data/records.csv` was reached by the directory comparator (expanding the root), then the zip comparator (extracting the archive), then another directory comparator (expanding the extracted contents), then the CSV comparator (parsing the file). At extract time, we need to reconstruct that physical access chain from the migration JSON alone.

## Decision

**Each DiffNode records its provenance: which comparator created it (`comparator`) and which transformers modified it (`transformed_by`, in order). The last plugin to touch a node owns its extraction.**

Concretely:

1. `DiffNode` gains two fields: `comparator: Option<String>` and `transformed_by: Vec<String>`. These are serialized into the migration JSON.

2. Comparators implement `reopen(pair, child_path, ctx)` to reconstruct physical access to a child item (directory resolves a path, zip re-extracts to a temp dir). They also implement `reopen_data(pair, ctx)` to parse leaf content into format-neutral form (`TabularData`, text, or binary).

3. Transformers implement `extract(data, node, aspect)` to format reopened data for the end user. For example, the column reorder detector formats a before/after column order summary.

4. `Controller::extract()` walks the ancestor chain from root to target node, calling `reopen` at each container level to reconstruct physical paths. At the leaf, it calls `reopen_data` on the comparator, then `extract` on the last transformer (or the comparator itself if no transformer modified the node).

The rule is simple: **whoever last touched the node understands it best and is responsible for explaining it to the user.**

## Why "last toucher" and not explicit registration?

The alternative was a separate `extract_registry` where plugins explicitly register which `(item_type, kind)` combinations they can extract. We rejected this because:

- It's redundant. The transformer already declared what it matches via `match_types`/`match_tags`/`match_kinds`. If it rewrites a node, it understands the node.
- It creates a coordination problem. A transformer author would need to register extraction handlers separately from the transform itself, and the two could drift out of sync.
- It doesn't handle the common case where no transformer fires. If the CSV comparator produces a `modify` node and no transformer touches it, the comparator should extract — but a registry-based approach would need the comparator to register as *both* a comparator and an extractor.

The `transformed_by` list makes this automatic: if the list is empty, the comparator extracts; otherwise, the last entry extracts.

## Why record provenance in the serialized migration?

Extract must work on a saved migration file, potentially on a different machine or at a later time. The migration JSON must contain enough information to reconstruct the access chain without re-running the diff. Storing `comparator` and `transformed_by` as strings (plugin names) makes this possible — the extract command looks up the named plugins in the current registry and calls their `reopen`/`extract` methods.

This does mean extract requires the same plugin set that produced the migration. A migration produced with a custom BioBinoc plugin can only be extracted if BioBinoc is installed. This is acceptable — the migration JSON itself is always readable (it's just JSON), only the `extract` verb requires the plugins.

## The reopen chain

Container comparators (directory, zip) implement `reopen` to reconstruct physical access. This is distinct from `compare` — `reopen` doesn't diff anything, it just resolves a child's physical path within the container. For directories, this is trivial (join the path). For zips, it re-extracts to a temp directory.

The chain is walked from root to target: directory → zip → directory → csv. Each `reopen` call produces an `ItemPair` pointing at the next level's physical files. At the leaf, `reopen_data` parses the files into `ReopenedData` (a format-neutral enum: `Tabular`, `Text`, or `Binary`), which is then passed to the extractor.

## Alternatives considered

- **Re-run the diff and intercept intermediate data:** Simpler to implement (no new traits), but wasteful for large datasets and doesn't work on saved migrations.
- **Store extracted data in the migration JSON:** Would balloon the migration size. The whole point of extract is on-demand access.
- **Generic `Extractor` trait separate from Comparator/Transformer:** Adds a third plugin axis. The "last toucher" rule achieves the same dispatch without a new concept.
