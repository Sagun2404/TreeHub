# Security Policy

## Supported Versions

Currently, we accept security reports only for the main branch of `treehub`.

| Version | Supported          |
| ------- | ------------------ |
| v0.1.x  | :white_check_mark: |

## Reporting a Vulnerability

We take the security of TreeHub seriously, especially because it involves an MCP server that may interact with your local environment, and a CLI tool.

If you discover a security vulnerability, please report it privately. **Do not disclose it publicly until a fix has been released.**

To report a vulnerability:
1. Email us at [INSERT CONTACT EMAIL] with "SECURITY: [Brief Description]" in the subject line.
2. Provide a detailed description of the issue, including steps to reproduce it.
3. If applicable, provide a proof-of-concept (PoC).

### Scope

The following are considered in-scope for security reports:
* **MCP Server Vulnerabilities**: e.g., path traversal (escaping the restricted file bounds), unauthorized execution, or exposing sensitive local information.
* **CLI Vulnerabilities**: e.g., arbitrary code execution or command injection when processing maliciously crafted `manifest.json` or `tree.json` files.
* **Data Integrity**: Bypassing SHA-256 checksum validations during index pull.

The following are out-of-scope:
* Vulnerabilities in third-party dependencies (unless they are combined in a way unique to TreeHub). Please report those directly to the upstream maintainer.
* Bugs that do not pose a security risk (e.g., UI glitches, failure to parse a specific `llms.txt`). Use the normal issue tracker for these.

### Timelines

We aim to acknowledge all reports within 48 hours and provide a fix within 90 days. We will coordinate the public disclosure with you so that you can receive proper credit (if desired).
