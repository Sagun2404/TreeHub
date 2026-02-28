# TreeHub — Product Design Document

## 1. Overview

| Field | Value |
|-------|-------|
| **Name** | TreeHub |
| **Tagline** | The Wikipedia of AI Indices |
| **Mission** | Eliminate indexing overhead for AI-powered documentation tools by providing pre-built, versioned PageIndex trees for popular developer platforms. |
| **Status** | MVP / Open Source |
| **License** | MIT |

---

## 2. Problem Statement

### Current Pain Points

| Pain Point | Impact |
|------------|--------|
| **Time** | Building a PageIndex tree takes 30–50 minutes per documentation site |
| **Cost** | Indexing requires thousands of LLM tokens (API costs scale with usage) |
| **Redundancy** | Every developer/agent repeats the same indexing work |
| **Version Drift** | No standardized way to access documentation for legacy versions |
| **Trust** | No verification of index integrity or provenance |

### Target Users

- AI agent developers building doc-aware tools
- Developers using reasoning-based RAG frameworks (PageIndex, etc.)
- MCP server creators needing fast document retrieval
- Technical writers maintaining documentation structures

---

## 3. Solution

A community-maintained repository of pre-computed PageIndex JSON trees, distributed via Git and MCP server.

### Core Value Propositions

| Value | Description |
|-------|-------------|
| **Zero-Latency Setup** | `git pull` → instant production-ready indices |
| **Cost Savings** | Amortize indexing costs across the community |
| **Versioned Snapshots** | Access docs for any platform version (e.g., `supabase-v2.1.0`) |
| **Verified Integrity** | Cryptographic provenance and build transparency |
| **Standard Format** | Works with any LLM or RAG framework |

---

## 4. Scope

### In Scope (MVP)

- [x] Pre-built PageIndex trees for top 10–15 developer platforms
- [x] Semantic versioning (`platform-vX.Y.Z-tree.json`)
- [x] Date-based snapshots (`platform-YYYY-MM-DD-tree.json`)
- [x] Weekly automated re-indexing via GitHub Actions
- [x] MCP server for IDE/agent integration
- [x] CLI tool for local index management
- [x] Integrity verification and provenance tracking

### Out of Scope (V1)

| Feature | Rationale |
|---------|-----------|
| Embeddings/vector stores | Focus on structure, not semantics |
| Real-time indexing | Weekly cadence sufficient for docs |
| Private/enterprise documentation | Open source first; SaaS later |
| Web UI | GitHub is the interface |
| Full-text search index | Client-side fuzzy match only |

---

## 5. Technical Architecture

### Directory Structure

```
treehub/
├── indices/
│   ├── supabase/
│   │   ├── v2.1.0-tree.json
│   │   ├── v2.1.0-manifest.json      # metadata, checksums, stats, provenance
│   │   ├── 2025-02-28-tree.json      # date-based snapshot
│   │   └── latest.json               # symlink to latest version
│   ├── huggingface/
│   │   └── ...
│   └── _template/                    # contribution template
├── scripts/
│   ├── crawler.py                    # llms.txt fetcher with rate limiting
│   ├── indexer.py                    # PageIndex builder (GPT-4o-mini)
│   ├── validator.py                  # schema validation
│   └── differ.py                     # version diff generator
├── mcp-server/
│   └── server.py                     # MCP implementation
├── cli/
│   └── treehub.py                    # pip install treehub-cli
└── .github/
    └── workflows/
        ├── weekly-index.yml          # automation
        └── validate-pr.yml           # PR validation
```

### Data Schema

#### `tree.json`

```json
{
  "meta": {
    "platform": "supabase",
    "version": "2.1.0",
    "snapshot_date": "2025-02-28",
    "indexed_at": "2025-02-28T00:00:00Z",
    "source_url": "https://supabase.com/llms.txt",
    "tree_hash": "sha256:abc123...",
    "llms_txt_hash": "sha256:def456...",
    "pages_count": 847,
    "tokens_indexed": 125000,
    "indexer_version": "1.2.0",
    "indexed_by": "github-actions[bot]",
    "build_log_url": "https://github.com/treehub/indices/actions/runs/123"
  },
  "tree": {
    "root": {
      "id": "root",
      "title": "Supabase Documentation",
      "summary": "Open source Firebase alternative...",
      "content_hash": "sha256:xyz789...",
      "children": [
        {
          "id": "database",
          "title": "Database",
          "summary": "Postgres database management...",
          "content_hash": "sha256:ghi012...",
          "relationships": {
            "related": ["auth", "storage"],
            "next_page": "quickstart",
            "parent": "root"
          },
          "children": [...]
        }
      ]
    }
  }
}
```

#### `manifest.json`

```json
{
  "platform": "supabase",
  "version": "2.1.0",
  "snapshot_date": "2025-02-28",
  "files": {
    "tree": {
      "path": "v2.1.0-tree.json",
      "hash": "sha256:abc123...",
      "size_bytes": 456000
    }
  },
  "provenance": {
    "indexed_by": "github-actions[bot]",
    "indexer_version": "1.2.0",
    "llms_txt_hash": "sha256:def456...",
    "build_log_url": "https://github.com/.../actions/runs/123",
    "git_commit": "a1b2c3d"
  },
  "stats": {
    "pages_count": 847,
    "max_depth": 4,
    "tokens_indexed": 125000,
    "indexing_duration_seconds": 180
  },
  "schema_version": "1.0.0"
}
```

### Automation Pipeline

| Step | Action | Details |
|------|--------|---------|
| **Trigger** | Weekly cron + manual dispatch | Configurable per platform |
| **Crawl** | Fetch `llms.txt` | Rate-limited, retry with backoff |
| **Detect** | Compare hash with last index | Skip if unchanged |
| **Index** | Build tree via GPT-4o-mini | Cost: ~$0.50–2.00 per platform |
| **Validate** | JSON schema + integrity checks | Fail on schema mismatch |
| **Diff** | Generate changelog | Compare with previous version |
| **Commit** | Auto-PR with changelog | Human review for breaking changes |
| **Release** | Tag version, update `latest.json` | Atomic update |

---

## 6. MCP Server Specification

**Server Name:** `treehub`

### Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_platforms()` | Returns all available platforms | — |
| `list_versions(platform)` | Returns versions for a platform | `platform: string` |
| `fetch_tree(platform, version)` | Returns full tree JSON | `platform: string`, `version: string` |
| `query_tree(platform, version, path)` | Returns subtree at path | `platform: string`, `version: string`, `path: string` |
| `search_tree(platform, version, query)` | Returns relevant nodes (client-side fuzzy) | `platform: string`, `version: string`, `query: string`, `limit?: number` |
| `diff_versions(platform, v1, v2)` | Returns structural diff between versions | `platform: string`, `v1: string`, `v2: string` |
| `subscribe(platform)` | Register for new version notifications | `platform: string`, `webhook_url?: string` |

### Resources

| Resource | Description |
|----------|-------------|
| `treehub://{platform}/{version}/tree` | Full tree JSON |
| `treehub://{platform}/{version}/manifest` | Metadata and provenance |
| `treehub://{platform}/{version}/diff/{from_version}` | Changelog from previous version |

---

## 7. CLI Specification

### Installation

```bash
pip install treehub-cli
```

### Commands

```bash
# List available platforms
treehub list

# List versions for a platform
treehub versions supabase

# Pull specific version
treehub pull supabase@v2.1.0

# Pull latest (symlink, updates automatically)
treehub pull supabase@latest

# Preview before pulling
treehub preview supabase@v2.1.0 --max-depth 2

# Compare local vs remote
treehub status supabase@v2.1.0

# Verify integrity
treehub verify supabase@v2.1.0

# Show diff between versions
treehub diff supabase@v2.1.0 v2.0.0

# Export to other formats
treehub export supabase@v2.1.0 --format markdown --output ./docs-structure.md

# Local development (index your own docs)
treehub index ./my-docs --output ./my-tree.json

# Cache management
treehub cache ls
treehub cache clear
treehub cache prune --older-than 30d

# Subscribe to updates
treehub subscribe supabase --webhook https://my-app.com/webhook
```

---

## 8. Success Metrics

| Metric | Target (3 months) | Measurement |
|--------|-------------------|-------------|
| Platforms indexed | 15 | GitHub repo count |
| GitHub stars | 500 | GitHub API |
| Weekly active MCP users | 100 | MCP server telemetry (opt-in) |
| Community contributors | 10 | PR authors |
| Avg. time to first query | <5 seconds | CLI telemetry (opt-in) |
| Index freshness | <7 days | Last indexed timestamp |
| Verification pass rate | >99% | Automated validation |

---

## 9. Roadmap

### Phase 1: MVP (Weeks 1–4)

| Week | Deliverable | Success Criteria |
|------|-------------|------------------|
| 1 | Schema + 1 manual index (Supabase) | Validated tree.json, working crawler |
| 2 | MCP server + CLI core | `list`, `pull`, `verify` commands work |
| 3 | Automation pipeline | 5 platforms auto-indexed weekly |
| 4 | Launch + feedback | Hacker News post, 100 stars |

### Phase 2: Scale (Months 2–3)

- [ ] Expand to 15 platforms
- [ ] Community contribution workflow
- [ ] `diff_versions` and `subscribe` tools
- [ ] CLI `index` command for local docs
- [ ] Integration examples (LangChain, LlamaIndex, Vercel AI SDK)

### Phase 3: Sustainability (Months 4–6)

- [ ] Private indices (self-hosted)
- [ ] Real-time webhooks (paid tier)
- [ ] Analytics dashboard for platform teams
- [ ] Enterprise SLA offerings

---

## 10. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Rate limiting on source docs | Exponential backoff, respect robots.txt, cache aggressively |
| Large documentation sites (>10k pages) | Streaming indexer, depth limits, pagination |
| Schema drift | Strict versioning, migration scripts, backward compatibility |
| Malicious contributions | PR review, automated validation, provenance tracking |
| Platform removes `llms.txt` | Fallback to sitemap.xml, community mirrors |

---

## 11. Contributing

### Adding a New Platform

1. Open an issue with platform name and `llms.txt` URL
2. Use `scripts/crawler.py` to test fetch
3. Submit PR following `_template/` structure
4. Automated validation runs on PR
5. Merge triggers first index

### Schema Changes

- Schema versions follow SemVer
- Breaking changes require major version bump
- Migration period: 30 days minimum

---

## 12. Appendix

### Glossary

| Term | Definition |
|------|------------|
| **PageIndex** | Hierarchical semantic index of documentation pages |
| **llms.txt** | Emerging standard for LLM-optimized documentation |
| **MCP** | Model Context Protocol (Anthropic standard for tool integration) |
| **Provenance** | Cryptographic proof of index origin and integrity |

### Related Standards

- [llms.txt](https://llmstxt.org/) — Documentation format
- [MCP Specification](https://modelcontextprotocol.io/) — Tool integration
- [Sigstore](https://www.sigstore.dev/) — Future provenance enhancement

---

*Last updated: 2025-02-28*
*Version: 1.0.0*
```

This updated PDD includes all the improvements discussed: enhanced schema with relationships and content hashes, expanded MCP tools, date-based versioning, integrity verification, CLI export/local indexing capabilities, and a clearer risk mitigation section.