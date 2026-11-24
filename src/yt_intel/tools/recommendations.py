from .envelope import BoundPrincipal, ToolEnvelope, unavailable


async def recommendations(*, principal: BoundPrincipal) -> ToolEnvelope:
    """Recommend videos from the linked account signals."""
    return unavailable()
