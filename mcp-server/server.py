"""
TreeHub MCP Server — Exposes pre-built PageIndex trees via Model Context Protocol.

Run:
    python mcp-server/server.py
    # or via uvx: uvx treehub-mcp

MCP Tools:
    list_platforms()                         → All available platforms
    list_versions(platform)                  → Versions for a platform
    fetch_tree(platform, version)            → Full PageIndex tree
    query_tree(platform, version, path)      → Subtree at specific path
    search_tree(platform, version, query)    → Fuzzy search nodes
    diff_versions(platform, v1, v2)          → Structural diff between versions
    subscribe(platform)                      → Register for update notifications

MCP Resources:
    treehub://{platform}/{version}/tree      → Full tree JSON
    treehub://{platform}/{version}/manifest  → Metadata and provenance
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

# Resolve the indices directory relative to this file
SERVER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SERVER_DIR.parent
INDICES_DIR = PROJECT_ROOT / "indices"

# Add project root to path for importing scripts
sys.path.insert(0, str(PROJECT_ROOT))

mcp = FastMCP(
    "treehub",
    description="The Wikipedia of AI Indices — Pre-built, versioned PageIndex trees for popular developer platforms.",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_platform_dir(platform: str) -> Path:
    """Get the directory for a platform, raising if not found."""
    platform_dir = INDICES_DIR / platform
    if not platform_dir.is_dir():
        raise ValueError(f"Platform not found: {platform}")
    return platform_dir


def _load_tree(platform: str, version: str) -> dict:
    """Load a tree.json file for a platform@version."""
    platform_dir = _get_platform_dir(platform)

    # Handle "latest" version
    if version == "latest":
        latest_file = platform_dir / "latest.json"
        if latest_file.exists():
            return json.loads(latest_file.read_text(encoding="utf-8"))
        # Fall back to most recent versioned file
        tree_files = sorted(platform_dir.glob("*-tree.json"), reverse=True)
        if tree_files:
            return json.loads(tree_files[0].read_text(encoding="utf-8"))
        raise FileNotFoundError(f"No tree files found for {platform}")

    tree_file = platform_dir / f"{version}-tree.json"
    if not tree_file.exists():
        raise FileNotFoundError(f"Tree not found: {platform}@{version}")
    return json.loads(tree_file.read_text(encoding="utf-8"))


def _load_manifest(platform: str, version: str) -> dict:
    """Load a manifest.json file for a platform@version."""
    platform_dir = _get_platform_dir(platform)
    manifest_file = platform_dir / f"{version}-manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest not found: {platform}@{version}")
    return json.loads(manifest_file.read_text(encoding="utf-8"))


def _find_node_by_path(tree: dict, path: str) -> dict | None:
    """Navigate to a node by dot-separated path (e.g. 'database.quickstart')."""
    parts = path.strip(".").split(".")
    current = tree.get("tree", {}).get("root", {})

    for part in parts:
        if part == "root":
            continue
        found = False
        for child in current.get("children", []):
            if child.get("id") == part:
                current = child
                found = True
                break
        if not found:
            return None
    return current


def _search_nodes(
    node: dict, query: str, results: list[dict], path: str = "", limit: int = 10
) -> None:
    """Recursively search for nodes matching query (case-insensitive)."""
    if len(results) >= limit:
        return

    query_lower = query.lower()
    title = node.get("title", "")
    summary = node.get("summary", "")

    if query_lower in title.lower() or query_lower in summary.lower():
        results.append(
            {
                "id": node.get("id"),
                "title": title,
                "summary": summary,
                "path": path or "root",
            }
        )

    for child in node.get("children", []):
        child_path = f"{path}.{child.get('id')}" if path else child.get("id", "")
        _search_nodes(child, query, results, child_path, limit)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def list_platforms() -> list[dict[str, str]]:
    """List all available platforms with their latest version info."""
    platforms = []
    for platform_dir in sorted(INDICES_DIR.iterdir()):
        if not platform_dir.is_dir() or platform_dir.name.startswith("_"):
            continue

        tree_files = sorted(platform_dir.glob("*-tree.json"))
        versions = [f.stem.replace("-tree", "") for f in tree_files]

        platforms.append(
            {
                "platform": platform_dir.name,
                "versions_count": len(versions),
                "latest": versions[-1] if versions else "none",
            }
        )

    return platforms


@mcp.tool()
def list_versions(platform: str) -> list[dict[str, str]]:
    """List all available versions for a specific platform.

    Args:
        platform: Platform identifier (e.g. 'supabase', 'stripe').
    """
    platform_dir = _get_platform_dir(platform)
    tree_files = sorted(platform_dir.glob("*-tree.json"))

    versions = []
    for tf in tree_files:
        version = tf.stem.replace("-tree", "")
        manifest_file = platform_dir / f"{version}-manifest.json"

        info: dict[str, str] = {"version": version}
        if manifest_file.exists():
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            info["snapshot_date"] = manifest.get("snapshot_date", "")
            info["pages_count"] = str(manifest.get("stats", {}).get("pages_count", 0))

        versions.append(info)

    return versions


@mcp.tool()
def fetch_tree(platform: str, version: str = "latest") -> dict:
    """Fetch the full PageIndex tree for a platform version.

    Args:
        platform: Platform identifier (e.g. 'supabase').
        version: Version string (e.g. 'v2.1.0' or 'latest').
    """
    return _load_tree(platform, version)


@mcp.tool()
def query_tree(platform: str, version: str, path: str) -> dict:
    """Get a subtree at a specific path within the PageIndex.

    Args:
        platform: Platform identifier.
        version: Version string.
        path: Dot-separated path to the node (e.g. 'database.quickstart').
    """
    tree = _load_tree(platform, version)
    node = _find_node_by_path(tree, path)
    if node is None:
        raise ValueError(f"Path not found: {path} in {platform}@{version}")
    return node


@mcp.tool()
def search_tree(
    platform: str, version: str, query: str, limit: int = 10
) -> list[dict]:
    """Search for nodes matching a query string (fuzzy, case-insensitive).

    Args:
        platform: Platform identifier.
        version: Version string.
        query: Search query to match against titles and summaries.
        limit: Maximum number of results (default: 10).
    """
    tree = _load_tree(platform, version)
    results: list[dict] = []
    root = tree.get("tree", {}).get("root", {})
    _search_nodes(root, query, results, limit=limit)
    return results


@mcp.tool()
def diff_versions(platform: str, v1: str, v2: str) -> dict:
    """Generate a structural diff between two versions of a platform's index.

    Args:
        platform: Platform identifier.
        v1: Older version string.
        v2: Newer version string.
    """
    from scripts.differ import TreeDiffer

    tree_old = _load_tree(platform, v1)
    tree_new = _load_tree(platform, v2)

    differ = TreeDiffer()
    result = differ.diff(tree_old, tree_new, platform, v1, v2)
    return result.to_dict()


@mcp.tool()
def subscribe(platform: str, webhook_url: str | None = None) -> dict:
    """Register for notifications when a platform's index is updated.

    Args:
        platform: Platform identifier.
        webhook_url: Optional webhook URL for push notifications.
    """
    # Verify platform exists
    _get_platform_dir(platform)

    # TODO: Implement subscription storage (database / file-based)
    return {
        "status": "subscribed",
        "platform": platform,
        "webhook_url": webhook_url,
        "message": "You will be notified when new versions are published. "
        "(Subscription storage is not yet implemented.)",
    }


# ---------------------------------------------------------------------------
# MCP Resources
# ---------------------------------------------------------------------------


@mcp.resource("treehub://{platform}/{version}/tree")
def get_tree_resource(platform: str, version: str) -> str:
    """Full PageIndex tree JSON for a platform version."""
    tree = _load_tree(platform, version)
    return json.dumps(tree, indent=2)


@mcp.resource("treehub://{platform}/{version}/manifest")
def get_manifest_resource(platform: str, version: str) -> str:
    """Metadata and provenance for a platform version."""
    manifest = _load_manifest(platform, version)
    return json.dumps(manifest, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    mcp.run()


if __name__ == "__main__":
    main()
