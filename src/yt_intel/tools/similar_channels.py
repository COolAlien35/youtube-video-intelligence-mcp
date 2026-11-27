from .envelope import BoundPrincipal, ToolEnvelope, unavailable


async def similar_channels(channel: str, *, principal: BoundPrincipal) -> ToolEnvelope:
    """Find similar channels for an exact channel reference."""
    return unavailable()
