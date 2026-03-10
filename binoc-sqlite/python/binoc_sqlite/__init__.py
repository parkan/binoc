"""binoc-sqlite: SQLite comparator plugin for binoc.

Compares SQLite databases by diffing their schemas (tables, columns, types)
and row counts. Detects tables added/removed, columns added/removed/type-changed,
and row count changes.

Usage via entry point (automatic after ``pip install binoc-sqlite``)::

    binoc diff snapshot-a snapshot-b

Usage via Python API::

    import binoc
    import binoc_sqlite

    config = binoc.Config.default()
    config.add_comparator(binoc_sqlite.SqliteComparator())
    migration = binoc.diff("snapshot-a", "snapshot-b", config=config)
"""

import json

import binoc
from binoc_sqlite._binoc_sqlite import _SqliteComparatorCore


class SqliteComparator(binoc.Comparator):
    """Python comparator wrapping the Rust SQLite implementation.

    Delegates all comparison work to the native Rust code via JSON
    serialization. The Rust comparator handles schema reading, diffing,
    and DiffNode construction; this wrapper translates the result into
    the Python binoc types that the plugin bridge expects.
    """

    name = "binoc-sqlite.sqlite"
    extensions = [".sqlite", ".sqlite3", ".db"]

    def __init__(self):
        self._core = _SqliteComparatorCore()

    def compare(self, pair):
        result_json = self._core.compare_json(
            pair.left_path,
            pair.right_path,
            pair.logical_path,
        )
        if result_json is None:
            return binoc.Identical()

        return binoc.Leaf(_json_to_diffnode(json.loads(result_json)))


def _json_to_diffnode(d):
    """Reconstruct a binoc.DiffNode from its JSON-serialized form."""
    children = [_json_to_diffnode(c) for c in d.get("children", [])]
    return binoc.DiffNode(
        kind=d["kind"],
        item_type=d["item_type"],
        path=d["path"],
        summary=d.get("summary"),
        tags=d.get("tags", []),
        details=d.get("details", {}),
        children=children,
    )


def register(registry):
    """Entry point called by binoc's plugin discovery."""
    registry.register_comparator("binoc-sqlite.sqlite", SqliteComparator())
