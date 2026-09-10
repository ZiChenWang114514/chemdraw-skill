# Security Policy

## Supported Versions

Security fixes target the latest commit on the default branch and the latest GitHub release, when one exists. Older snapshots may not receive backports.

## Reporting

Do not publish credentials, private chemistry, laboratory records, or exploit details in a public issue. Use GitHub's private vulnerability reporting or a private security advisory for this repository. If that feature is unavailable, contact the repository owner through GitHub without attaching sensitive artifacts.

Include the affected version, tool name, minimal synthetic reproduction, expected impact, and whether a third-party upload or file overwrite is involved. Replace real molecules and documents with non-sensitive fixtures whenever possible.

## Security Boundaries

- This repository does not sandbox ChemDraw, Microsoft Office, Python dependencies, or the agent host itself.
- Remote DECIMER sends image bytes to a third party only after explicit confirmation. Users remain responsible for authorization and service terms.
- MCP tools can read and write paths accessible to their Windows user. Review requested paths and use a least-privilege account for untrusted inputs.
- CDXML, Office, RDF, PDF, and image files are untrusted input. Keep dependencies patched and avoid opening generated files outside an isolated test environment until validation succeeds.
- API keys and proxy credentials must be provided through local secret management or environment variables and must never be committed.
- Streamable HTTP binds to loopback by default. Non-loopback listening requires a bearer token and allowed Host configuration. Use an encrypted private network or HTTPS reverse proxy because the built-in HTTP listener does not provide TLS.
- `/health` contains only process status. Authenticated `/metrics` uses fixed tool/status labels and must not include molecule strings, filenames, document text, or request parameters.
