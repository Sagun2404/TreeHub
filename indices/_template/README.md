# Adding a New Platform to TreeHub

## Prerequisites

- The platform must have a publicly accessible `llms.txt` or equivalent documentation index.
- You should be familiar with the platform's documentation structure.

## Steps

### 1. Open an Issue

Open a [Platform Request issue](../../issues/new?template=platform_request.md) with:
- Platform name
- `llms.txt` URL (or equivalent)
- Versioning strategy (semver / date-based / both)

### 2. Create the Index Directory

```bash
mkdir -p indices/<platform-name>
```

### 3. Generate the Index

```bash
# Fetch the llms.txt
python scripts/crawler.py --platform <platform-name> --url <llms-txt-url>

# Build the PageIndex tree
python scripts/indexer.py --platform <platform-name> --version <version>

# Validate the output
python scripts/validator.py indices/<platform-name>/<version>-tree.json
```

### 4. Create Required Files

Each platform directory must contain:

| File | Description |
|------|-------------|
| `<version>-tree.json` | PageIndex tree (see `example-tree.json`) |
| `<version>-manifest.json` | Metadata & checksums (see `example-manifest.json`) |
| `latest.json` | Symlink to the latest version |

### 5. Register the Platform

Add an entry to `registry.json` at the project root:

```json
{
  "<platform-name>": {
    "source_url": "https://example.com/llms.txt",
    "versioning": "semver",
    "schedule": "weekly"
  }
}
```

### 6. Submit a PR

- Ensure `python scripts/validator.py` passes on your tree
- The CI workflow `validate-pr.yml` will run automatically
- A maintainer will review and merge

## File Format Reference

See `example-tree.json` and `example-manifest.json` in this directory for the expected schemas.
