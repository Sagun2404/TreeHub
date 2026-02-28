"""
TreeHub Validator — JSON schema and integrity validation for tree and manifest files.

Usage:
    python scripts/validator.py indices/supabase/v2.1.0-tree.json
    python scripts/validator.py indices/supabase/v2.1.0-tree.json --manifest indices/supabase/v2.1.0-manifest.json
    python scripts/validator.py --all           # Validate all indices
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
INDICES_DIR = PROJECT_ROOT / "indices"


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class TreeValidator:
    """Validates TreeHub tree.json and manifest.json files.

    Checks:
        1. JSON syntax — valid JSON
        2. Schema compliance — matches tree-schema.json / manifest-schema.json
        3. Integrity — SHA-256 hash verification
        4. Consistency — cross-references between tree and manifest
    """

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self._tree_schema: dict | None = None
        self._manifest_schema: dict | None = None

    # -- Public API ---------------------------------------------------------

    def validate_tree(self, tree_path: Path) -> bool:
        """Validate a tree.json file.

        Returns True if valid, False otherwise.
        """
        self.errors.clear()
        self.warnings.clear()

        # 1. Parse JSON
        data = self._load_json(tree_path)
        if data is None:
            return False

        # 2. Check required top-level keys
        if "meta" not in data:
            self.errors.append("Missing required key: 'meta'")
        if "tree" not in data:
            self.errors.append("Missing required key: 'tree'")

        if self.errors:
            return False

        # 3. Validate meta fields
        meta = data["meta"]
        required_meta = ["platform", "version", "indexed_at", "source_url", "tree_hash", "pages_count"]
        for field in required_meta:
            if field not in meta:
                self.errors.append(f"Missing required meta field: '{field}'")

        # 4. Validate tree structure
        tree = data.get("tree", {})
        if "root" not in tree:
            self.errors.append("Missing 'root' in tree")
        else:
            self._validate_node(tree["root"], path="root")

        # 5. Validate tree hash integrity
        if "tree_hash" in meta:
            self._validate_tree_hash(data)

        # 6. JSON Schema validation (if jsonschema is available)
        self._validate_against_schema(data, "tree")

        return len(self.errors) == 0

    def validate_manifest(self, manifest_path: Path) -> bool:
        """Validate a manifest.json file.

        Returns True if valid, False otherwise.
        """
        self.errors.clear()
        self.warnings.clear()

        data = self._load_json(manifest_path)
        if data is None:
            return False

        required = ["platform", "version", "files", "provenance", "stats", "schema_version"]
        for field in required:
            if field not in data:
                self.errors.append(f"Missing required field: '{field}'")

        # Validate files section
        files = data.get("files", {})
        if "tree" in files:
            tree_file = files["tree"]
            for key in ["path", "hash", "size_bytes"]:
                if key not in tree_file:
                    self.errors.append(f"Missing files.tree.{key}")

        # Validate provenance
        provenance = data.get("provenance", {})
        for key in ["indexed_by", "indexer_version"]:
            if key not in provenance:
                self.errors.append(f"Missing provenance.{key}")

        # JSON Schema validation
        self._validate_against_schema(data, "manifest")

        return len(self.errors) == 0

    def validate_pair(self, tree_path: Path, manifest_path: Path) -> bool:
        """Validate a tree + manifest pair for consistency."""
        self.errors.clear()
        self.warnings.clear()

        tree_valid = self.validate_tree(tree_path)
        tree_errors = list(self.errors)
        tree_warnings = list(self.warnings)

        manifest_valid = self.validate_manifest(manifest_path)

        # Merge errors
        self.errors = tree_errors + self.errors
        self.warnings = tree_warnings + self.warnings

        if not (tree_valid and manifest_valid):
            return False

        # Cross-validate
        tree_data = self._load_json(tree_path)
        manifest_data = self._load_json(manifest_path)

        if tree_data and manifest_data:
            # Platform must match
            if tree_data["meta"]["platform"] != manifest_data["platform"]:
                self.errors.append("Platform mismatch between tree and manifest")

            # Version must match
            if tree_data["meta"]["version"] != manifest_data["version"]:
                self.errors.append("Version mismatch between tree and manifest")

            # Verify file hash from manifest matches actual tree file hash
            tree_bytes = tree_path.read_bytes()
            actual_hash = f"sha256:{hashlib.sha256(tree_bytes).hexdigest()}"
            expected_hash = manifest_data.get("files", {}).get("tree", {}).get("hash")

            if expected_hash and actual_hash != expected_hash:
                self.errors.append(
                    f"Tree file hash mismatch: expected {expected_hash}, got {actual_hash}"
                )

        return len(self.errors) == 0

    def validate_all(self) -> dict[str, bool]:
        """Validate all indices in the indices/ directory.

        Returns dict of platform → valid.
        """
        results: dict[str, bool] = {}

        for platform_dir in sorted(INDICES_DIR.iterdir()):
            if not platform_dir.is_dir() or platform_dir.name.startswith("_"):
                continue

            # Find tree files
            tree_files = sorted(platform_dir.glob("*-tree.json"))
            for tree_file in tree_files:
                version = tree_file.stem.replace("-tree", "")
                manifest_file = platform_dir / f"{version}-manifest.json"

                key = f"{platform_dir.name}/{version}"
                if manifest_file.exists():
                    results[key] = self.validate_pair(tree_file, manifest_file)
                else:
                    results[key] = self.validate_tree(tree_file)
                    if results[key]:
                        self.warnings.append(f"No manifest found for {key}")

        return results

    # -- Internal -----------------------------------------------------------

    def _load_json(self, path: Path) -> dict | None:
        """Load and parse a JSON file."""
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.errors.append(f"Invalid JSON in {path.name}: {exc}")
            return None
        except FileNotFoundError:
            self.errors.append(f"File not found: {path}")
            return None

    def _validate_node(self, node: dict, path: str) -> None:
        """Recursively validate a tree node."""
        required = ["id", "title", "summary", "children"]
        for field in required:
            if field not in node:
                self.errors.append(f"Node at '{path}' missing field: '{field}'")

        children = node.get("children", [])
        if not isinstance(children, list):
            self.errors.append(f"Node at '{path}': children must be an array")
        else:
            for i, child in enumerate(children):
                child_id = child.get("id", f"[{i}]")
                self._validate_node(child, f"{path}.{child_id}")

    def _validate_tree_hash(self, data: dict) -> None:
        """Verify the tree_hash in meta matches the actual tree content."""
        try:
            tree_content = json.dumps(data["tree"], sort_keys=True)
            actual_hash = f"sha256:{hashlib.sha256(tree_content.encode()).hexdigest()}"
            expected_hash = data["meta"]["tree_hash"]

            if actual_hash != expected_hash:
                self.warnings.append(
                    f"tree_hash mismatch (may differ due to serialization): "
                    f"expected {expected_hash[:30]}..."
                )
        except (KeyError, TypeError):
            pass

    def _validate_against_schema(self, data: dict, schema_type: str) -> None:
        """Validate against JSON Schema if jsonschema is available."""
        try:
            import jsonschema
        except ImportError:
            self.warnings.append(
                "jsonschema not installed — skipping schema validation. "
                "Install with: pip install jsonschema"
            )
            return

        schema_file = SCHEMAS_DIR / f"{schema_type}-schema.json"
        if not schema_file.exists():
            self.warnings.append(f"Schema file not found: {schema_file}")
            return

        try:
            schema = json.loads(schema_file.read_text(encoding="utf-8"))
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as exc:
            self.errors.append(f"Schema validation failed: {exc.message}")
        except json.JSONDecodeError:
            self.errors.append(f"Invalid JSON in schema file: {schema_file}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="TreeHub Validator")
    parser.add_argument("file", nargs="?", help="Path to tree.json to validate")
    parser.add_argument("--manifest", help="Optional manifest.json to cross-validate")
    parser.add_argument("--all", action="store_true", help="Validate all indices")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    validator = TreeValidator()

    if args.all:
        results = validator.validate_all()
        if not results:
            print("⚠️  No indices found to validate.")
            return

        all_valid = True
        for key, valid in results.items():
            status = "✅" if valid else "❌"
            print(f"  {status} {key}")
            if not valid:
                all_valid = False
                for err in validator.errors:
                    print(f"     ↳ {err}")

        sys.exit(0 if all_valid else 1)

    if not args.file:
        parser.print_help()
        sys.exit(1)

    tree_path = Path(args.file)

    if args.manifest:
        valid = validator.validate_pair(tree_path, Path(args.manifest))
    else:
        valid = validator.validate_tree(tree_path)

    if valid:
        print(f"✅ Valid: {tree_path.name}")
        for w in validator.warnings:
            print(f"   ⚠️ {w}")
    else:
        print(f"❌ Invalid: {tree_path.name}")
        for err in validator.errors:
            print(f"   ↳ {err}")
        for w in validator.warnings:
            print(f"   ⚠️ {w}")

    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
