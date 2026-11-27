# Redacting JSON logs in concurrent Python requests

## Source

Python 3.12 [logging reference](https://docs.python.org/3.12/library/logging.html#logging.LogRecord.getMessage), [filters](https://docs.python.org/3.12/library/logging.html#filter-objects) and [context variables](https://docs.python.org/3.12/library/contextvars.html#asyncio-support). Project scope comes from the SRS v1.0 candidate §§6–7 and the Phase 2 logging contract.

## Ingested by / date

Person D · 2026-11-23 · AI-assisted research note

## Summary

Python constructs a log record before a handler writes it.
A message template and its substitution arguments can carry different pieces of a credential.
The project formatter therefore inspects the rendered message as well as separately supplied fields.
A request-scoped ContextVar lets the formatter associate an event with the currently running async task.
JSON serialization keeps embedded line breaks inside one event and makes its fields inspectable in tests.

## Key facts

- LogRecord.getMessage() applies message substitution. The extra argument supplies additional record attributes. See the logging reference above.
- A handler filter sees records reaching that handler. Filters and formatters occupy distinct stages in Python’s logging pipeline. See the filters reference.
- asyncio supports context variables directly. Restoring the token returned by set() recovers the previous context value. See the context variables reference.
- The SRS requires protection of secrets in logs. Matching credential field names and known token patterns is a project control. Callers still choose public event data.

## Relevance

SEC-06–09 and NFR-13–24. Test a formatted message, an exception message and nested extras separately, with synthetic credentials. Correlate concurrent requests using distinct IDs.

## Open questions / risks

B’s server configuration must route relevant application logs through the configured handler. Independently configured third-party handlers need inspection during integration.

## Links

[Redacting JSON logging PR](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/5) · [Request-context contract](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/3)
