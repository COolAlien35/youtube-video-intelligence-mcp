# Offline fixture policy

SRS §5.1 and TQ-5 require synthetic or sanitized fixtures. Author these examples from public resource schemas and invented values. Never record live API traffic. Keep real user data, emails, OAuth grants, cookies and live credentials out of fixtures and Git history.

Store provider response JSON below tests/fixtures/youtube/. Use endpoint-based names and a stable case or page suffix. Keep items, pageInfo and applicable nextPageToken fields in their raw shapes so tests exercise the normalizer. Use an account-specific directory or explicit account key for private collections. Every token-like value must start with FAKE_ and synthetic email addresses must end in @example.invalid.

Before committing a case, document the behavior it covers, regenerate twice and compare outputs, inspect the diff for identifying information and secrets, then run the fixture safety scan and the consuming tests. Review missing fields and empty arrays separately. Never copy production failures into the repository.

Video IDs use SYNV_ (11 characters total), channel IDs use UCSYN (24 characters), playlist IDs use PLSYN and handles use @syn_. Run python scripts/generate_fixtures.py to rebuild the catalogue. Search files are keyed by topic and page; the duplicate at the page boundary and the unavailable final ID are deliberate.
