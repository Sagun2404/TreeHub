"""
TreeHub Indexer — Builds PageIndex trees from crawled llms.txt content.

Usage:
    python scripts/indexer.py --platform supabase --version v2.1.0
    python scripts/indexer.py --platform supabase --version v2.1.0 --input ./indices/supabase/llms.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_INDICES_DIR = Path("indices")
DEFAULT_MODEL = "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class IndexerConfig:
    """Configuration for the PageIndex builder."""

    indices_dir: Path = DEFAULT_INDICES_DIR
    model: str = DEFAULT_MODEL
    api_key: str | None = None
    max_depth: int = 5
    indexer_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.environ.get("OPENAI_API_KEY")


@dataclass
class TreeNode:
    """A single node in the PageIndex tree."""

    id: str
    title: str
    summary: str
    content_hash: str = ""
    relationships: dict | None = None
    children: list[TreeNode] | None = None

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        node: dict = {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "content_hash": self.content_hash,
        }
        if self.relationships:
            node["relationships"] = self.relationships
        node["children"] = [c.to_dict() for c in (self.children or [])]
        return node


# ---------------------------------------------------------------------------
# Indexer
# ---------------------------------------------------------------------------


class PageIndexBuilder:
    """Builds hierarchical PageIndex trees from documentation content.

    This is a boilerplate implementation. The actual LLM-based summarization
    should be implemented by replacing the `_summarize` method with real
    API calls to GPT-4o-mini (or equivalent).

    Pipeline:
        1. Parse llms.txt into sections
        2. Build hierarchy from heading structure
        3. Generate summaries via LLM (stub — returns placeholder)
        4. Compute content hashes
        5. Output tree.json + manifest.json
    """

    def __init__(self, config: IndexerConfig | None = None) -> None:
        self.config = config or IndexerConfig()

    # -- Public API ---------------------------------------------------------

    def build(
        self,
        platform: str,
        version: str,
        content: str,
        *,
        source_url: str = "",
        llms_txt_hash: str = "",
    ) -> tuple[dict, dict]:
        """Build a PageIndex tree from raw content.

        Args:
            platform: Platform identifier.
            version: Version string.
            content: Raw llms.txt content.
            source_url: Original source URL.
            llms_txt_hash: Hash of the source content.

        Returns:
            Tuple of (tree_dict, manifest_dict).
        """
        logger.info("Building index for %s@%s", platform, version)

        # Parse content into sections
        sections = self._parse_sections(content)

        # Build tree
        root = self._build_tree(platform, sections)

        # Assemble tree.json
        now = datetime.now(timezone.utc)
        tree_content = json.dumps(root.to_dict(), indent=2)
        tree_hash = f"sha256:{hashlib.sha256(tree_content.encode()).hexdigest()}"

        tree_dict = {
            "meta": {
                "platform": platform,
                "version": version,
                "snapshot_date": now.strftime("%Y-%m-%d"),
                "indexed_at": now.isoformat(),
                "source_url": source_url,
                "tree_hash": tree_hash,
                "llms_txt_hash": llms_txt_hash or None,
                "pages_count": self._count_nodes(root),
                "tokens_indexed": len(content.split()),
                "indexer_version": self.config.indexer_version,
                "indexed_by": "manual",
                "build_log_url": None,
            },
            "tree": {"root": root.to_dict()},
        }

        # Assemble manifest.json
        tree_bytes = json.dumps(tree_dict, indent=2).encode()
        manifest_dict = {
            "platform": platform,
            "version": version,
            "snapshot_date": now.strftime("%Y-%m-%d"),
            "files": {
                "tree": {
                    "path": f"{version}-tree.json",
                    "hash": f"sha256:{hashlib.sha256(tree_bytes).hexdigest()}",
                    "size_bytes": len(tree_bytes),
                }
            },
            "provenance": {
                "indexed_by": "manual",
                "indexer_version": self.config.indexer_version,
                "llms_txt_hash": llms_txt_hash or None,
                "build_log_url": None,
                "git_commit": None,
            },
            "stats": {
                "pages_count": self._count_nodes(root),
                "max_depth": self._max_depth(root),
                "tokens_indexed": len(content.split()),
                "indexing_duration_seconds": 0,
            },
            "schema_version": "1.0.0",
        }

        return tree_dict, manifest_dict

    def build_and_save(
        self,
        platform: str,
        version: str,
        content: str,
        *,
        source_url: str = "",
        llms_txt_hash: str = "",
    ) -> tuple[Path, Path]:
        """Build and save tree.json + manifest.json to disk.

        Returns:
            Tuple of (tree_path, manifest_path).
        """
        tree_dict, manifest_dict = self.build(
            platform,
            version,
            content,
            source_url=source_url,
            llms_txt_hash=llms_txt_hash,
        )

        out_dir = self.config.indices_dir / platform
        out_dir.mkdir(parents=True, exist_ok=True)

        tree_path = out_dir / f"{version}-tree.json"
        manifest_path = out_dir / f"{version}-manifest.json"

        tree_path.write_text(json.dumps(tree_dict, indent=2), encoding="utf-8")
        manifest_path.write_text(
            json.dumps(manifest_dict, indent=2), encoding="utf-8"
        )

        logger.info("Saved %s and %s", tree_path, manifest_path)
        return tree_path, manifest_path

    # -- Internal -----------------------------------------------------------

    def _parse_sections(self, content: str) -> list[dict]:
        """Parse llms.txt content into a list of sections.

        Each section has: title, level (heading depth), body.
        """
        sections: list[dict] = []
        current: dict | None = None

        for line in content.splitlines():
            stripped = line.strip()

            # Detect markdown headings
            if stripped.startswith("#"):
                if current:
                    sections.append(current)
                level = len(stripped) - len(stripped.lstrip("#"))
                title = stripped.lstrip("#").strip()
                current = {"title": title, "level": level, "body": ""}
            elif current is not None:
                current["body"] += line + "\n"
            else:
                # Content before any heading → root preamble
                if not sections and not current:
                    current = {"title": "Overview", "level": 1, "body": line + "\n"}

        if current:
            sections.append(current)

        return sections

    def _build_tree(self, platform: str, sections: list[dict]) -> TreeNode:
        """Build a tree from parsed sections."""
        root = TreeNode(
            id="root",
            title=f"{platform.title()} Documentation",
            summary=f"Documentation index for {platform}.",
            children=[],
        )

        if not sections:
            return root

        # Simple flat-to-tree: group by heading level
        stack: list[tuple[int, TreeNode]] = [(0, root)]

        for section in sections:
            node_id = section["title"].lower().replace(" ", "-")
            node_id = "".join(c for c in node_id if c.isalnum() or c == "-")

            body = section["body"].strip()
            summary = self._summarize(section["title"], body)
            content_hash = f"sha256:{hashlib.sha256(body.encode()).hexdigest()[:24]}"

            node = TreeNode(
                id=node_id,
                title=section["title"],
                summary=summary,
                content_hash=content_hash,
                children=[],
            )

            level = section["level"]

            # Pop stack until we find a parent at a lower level
            while stack and stack[-1][0] >= level:
                stack.pop()

            if stack:
                parent = stack[-1][1]
                if parent.children is None:
                    parent.children = []
                parent.children.append(node)
                node.relationships = {
                    "related": [],
                    "next_page": None,
                    "parent": parent.id,
                }

            stack.append((level, node))

        return root

    def _summarize(self, title: str, body: str) -> str:
        """Generate a summary for a section.

        TODO: Replace with actual LLM API call (GPT-4o-mini).
        Currently returns a placeholder summary.
        """
        if body:
            # Use first 200 chars as a basic summary
            preview = body[:200].replace("\n", " ").strip()
            return f"{preview}..." if len(body) > 200 else preview
        return f"Documentation section: {title}"

    def _count_nodes(self, node: TreeNode) -> int:
        """Count total nodes in the tree."""
        count = 1
        for child in node.children or []:
            count += self._count_nodes(child)
        return count

    def _max_depth(self, node: TreeNode, depth: int = 0) -> int:
        """Compute max depth of the tree."""
        if not node.children:
            return depth
        return max(self._max_depth(c, depth + 1) for c in node.children)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="TreeHub PageIndex Builder")
    parser.add_argument("--platform", required=True, help="Platform identifier")
    parser.add_argument("--version", required=True, help="Version string")
    parser.add_argument(
        "--input",
        default=None,
        help="Path to llms.txt (default: indices/<platform>/llms.txt)",
    )
    parser.add_argument("--output", default=str(DEFAULT_INDICES_DIR), help="Output dir")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    input_path = Path(args.input) if args.input else Path(args.output) / args.platform / "llms.txt"
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        print("   Run crawler.py first to fetch llms.txt.")
        return

    content = input_path.read_text(encoding="utf-8")
    config = IndexerConfig(indices_dir=Path(args.output))
    builder = PageIndexBuilder(config)

    tree_path, manifest_path = builder.build_and_save(
        args.platform,
        args.version,
        content,
    )

    print(f"✅ Indexed {args.platform}@{args.version}")
    print(f"   Tree:     {tree_path}")
    print(f"   Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
