from .envelope import BoundPrincipal, ToolEnvelope, unavailable


async def propose_playlist(
    topic: str,
    max_total_seconds: int,
    max_video_seconds: int | None = None,
    language: str | None = None,
    visibility: str = "private",
    *,
    principal: BoundPrincipal,
) -> ToolEnvelope:
    """Preview a playlist subject to the supplied duration and language constraints."""
    return unavailable()
