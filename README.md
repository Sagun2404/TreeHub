
# 🌳 TreeHub

> **The Wikipedia of AI Indices** — Pre-built, versioned PageIndex trees for popular developer platforms.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Server](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io/)
[![Index Count](https://img.shields.io/badge/Platforms-5-green)]()

Eliminate indexing overhead. Stop rebuilding the same PageIndex trees. Focus on building, not crawling.

---

## The Problem

Building AI-powered documentation tools today means:

- ⏱️ **30–50 minutes** to index a docs site
- 💸 **$2–10** in LLM API costs per platform
- 🔄 **Redundant work** — every developer repeats the same crawling
- 📉 **Version drift** — no standard way to access legacy docs

---

## The Solution

TreeHub provides **pre-computed, versioned PageIndex trees** distributed via Git and MCP:

```bash
# Get production-ready indices in seconds
treehub pull supabase@latest
```

- ✅ **Zero-latency setup** — `git pull` → instant indices
- ✅ **Cost amortized** — community bears indexing cost once
- ✅ **Versioned snapshots** — `supabase-v2.1.0`, `stripe-v2024-12`, etc.
- ✅ **Weekly updates** — automated re-indexing via GitHub Actions

---

## Quick Start

### CLI

```bash
# Install
pip install treehub-cli

# List available platforms
treehub list

# Pull latest Supabase index
treehub pull supabase@latest

# Pull specific version
treehub pull supabase@v2.1.0

# Verify integrity
treehub verify supabase@v2.1.0
```

### MCP Server

Add to your Claude Desktop / Cursor config:

```json
{
  "mcpServers": {
    "treehub": {
      "command": "uvx",
      "args": ["treehub-mcp"]
    }
  }
}
```

**Available Tools:**

| Tool | Description |
|------|-------------|
| `list_platforms()` | All available platforms |
| `list_versions(platform)` | Versions for a platform |
| `fetch_tree(platform, version)` | Full PageIndex tree |
| `query_tree(platform, version, path)` | Subtree at specific path |
| `search_tree(platform, version, query)` | Fuzzy search nodes |

---

## Repository Structure

```
treehub/
├── indices/                    # Pre-built PageIndex trees
│   ├── supabase/
│   │   ├── v2.1.0-tree.json   # PageIndex tree
│   │   ├── v2.1.0-manifest.json  # Metadata & checksums
│   │   └── latest.json -> v2.1.0-tree.json  # Symlink
│   ├── stripe/
│   ├── vercel/
│   └── _template/             # Contribution template
├── mcp-server/                # MCP server implementation
├── cli/                       # treehub-cli source
├── scripts/                   # Indexing automation
│   ├── crawler.py            # llms.txt fetcher
│   ├── indexer.py            # PageIndex builder (GPT-4o-mini)
│   └── validator.py          # Schema validation
└── .github/workflows/         # Weekly re-indexing
```

---

## Data Schema

Each index includes metadata and hierarchical tree structure:

```json
{
  "meta": {
    "platform": "supabase",
    "version": "2.1.0",
    "indexed_at": "2025-02-28T00:00:00Z",
    "source_url": "https://supabase.com/llms.txt",
    "tree_hash": "sha256:abc123...",
    "pages_count": 847,
    "tokens_indexed": 125000
  },
  "tree": {
    "root": {
      "title": "Supabase Documentation",
      "summary": "Open source Firebase alternative...",
      "children": [
        {
          "title": "Database",
          "summary": "Postgres database management...",
          "children": [...]
        }
      ]
    }
  }
}
```

---

## Supported Platforms (MVP)

| Platform | Versions | Status |
|----------|----------|--------|
| Supabase | v2.1.0, latest | ✅ Live |
| Stripe | v2024-12, latest | ✅ Live |
| Vercel | latest | ✅ Live |
| Hugging Face | latest | 🔄 Indexing |
| OpenAI | latest | 📋 Planned |

**Want a new platform?** [Request it](../../issues/new?template=platform_request.md) or [contribute one](#contributing).

---

## Feature Scope

### ✅ In Scope (MVP)

- [x] Pre-built PageIndex trees for top 5 platforms
- [x] Semantic versioning (`platform-vX.Y.Z-tree.json`)
- [x] Weekly automated re-indexing via GitHub Actions
- [x] MCP server for IDE/agent integration
- [x] CLI tool for local index management
- [x] JSON schema validation
- [x] Integrity verification (SHA-256 checksums)

### 🚧 Out of Scope (V1)

- Embeddings/vector stores (use your own)
- Real-time indexing (weekly batch only)
- Private/enterprise documentation
- Web UI (GitHub is the interface)
- Full-text search indexes (PageIndex trees only)

### 🔮 Future (Post-MVP)

- [ ] 15+ platforms indexed
- [ ] Diff between versions (`treehub diff supabase@v2.0.0 v2.1.0`)
- [ ] Subscribe to platform updates
- [ ] Custom index submissions
- [ ] REST API endpoint

---

## Automation Pipeline

Every week, GitHub Actions:

1. **Crawl** — Fetch `llms.txt` from registered platforms
2. **Detect** — Compare hash with last index
3. **Index** — Build tree via GPT-4o-mini (~$0.50–2.00/platform)
4. **Validate** — JSON schema + integrity checks
5. **Commit** — Auto-PR with changelog
6. **Release** — Tag version, update `latest.json`

**Cost:** ~$10/month to keep 10 platforms fresh.

---

## Contributing

### Add a New Platform

1. Check `indices/_template/` for the structure
2. Open an issue with the `platform-request` label
3. Or submit a PR with:
   - `indices/{platform}/vX.Y.Z-tree.json`
   - `indices/{platform}/vX.Y.Z-manifest.json`
   - Entry in `registry.json`

### Development

```bash
git clone https://github.com/yourusername/treehub.git
cd treehub

# Install CLI locally
pip install -e ./cli

# Run validation
python scripts/validator.py indices/supabase/v2.1.0-tree.json

# Test MCP server
cd mcp-server && python server.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## Why PageIndex?

PageIndex trees are **hierarchical semantic indices**—structured maps of documentation that capture:

- Section hierarchy (H1 → H2 → H3)
- Content summaries (LLM-generated)
- Page relationships

Unlike flat embeddings, trees preserve structure that reasoning models (Claude, o3, etc.) can navigate efficiently. TreeHub makes this pattern **zero-cost** to adopt.

---

## License

MIT — see [LICENSE](LICENSE)

---

## Acknowledgments

- Built for the [Model Context Protocol](https://modelcontextprotocol.io/)
- Inspired by `llms.txt` proposal from [Anthropic](https://www.anthropic.com/)
- PageIndex pattern from reasoning-based RAG frameworks

---

**[⭐ Star this repo](https://github.com/yourusername/treehub)** to follow our progress toward 15 platforms!
```

