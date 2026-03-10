"""Plugin discovery via Python entry points.

Third-party packages register binoc plugins by declaring an entry point
in the ``"binoc.plugins"`` group.  Each entry point should resolve to a
callable that accepts a :class:`~binoc.PluginRegistry` and populates it
with comparators, transformers, and/or outputters.

Example ``pyproject.toml`` for a third-party plugin package::

    [project.entry-points."binoc.plugins"]
    biobinoc = "biobinoc:register"

Where ``biobinoc.register`` looks like::

    def register(registry):
        from biobinoc.fasta import FastaComparator
        registry.register_comparator("biobinoc.fasta", FastaComparator())
"""

import importlib.metadata
import logging

logger = logging.getLogger("binoc")


def discover_plugins(registry):
    """Scan installed packages for binoc plugin entry points.

    Each entry point in the ``"binoc.plugins"`` group should be a callable
    that accepts a :class:`~binoc.PluginRegistry` and registers plugins
    into it.
    """
    eps = importlib.metadata.entry_points(group="binoc.plugins")
    for ep in eps:
        logger.debug("Loading plugin entry point: %s (from %s)", ep.name, ep.value)
        try:
            register_fn = ep.load()
            register_fn(registry)
        except Exception:
            logger.exception("Failed to load binoc plugin %r", ep.name)
