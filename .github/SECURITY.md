# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, **please do not open a public issue.**

Instead, use GitHub's **private vulnerability reporting**:

1. Go to the [Security tab](https://github.com/COolAlien35/youtube-video-intelligence-mcp/security) of this repository.
2. Click **"Report a vulnerability"**.
3. Fill in the details and submit.

We will acknowledge your report within 48 hours and work with you to understand and address the issue.

## Scope

This policy covers:

- The `youtube-video-intelligence-mcp` repository and its code
- Any deployed instances of the MCP server
- API keys, tokens, or credentials related to the project

## Security Practices

- **Secret scanning** and **push protection** are enabled on this repository.
- **gitleaks** scans every commit in CI.
- No real API keys, tokens, or user data are committed to the repository.
- All secrets are stored in Render environment variables or GitHub Secrets, never in git.

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ |
| Other branches | ❌ |
