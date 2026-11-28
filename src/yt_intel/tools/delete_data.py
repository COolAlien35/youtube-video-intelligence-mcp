from .envelope import BoundPrincipal, ToolEnvelope, unavailable


async def delete_data(*, principal: BoundPrincipal) -> ToolEnvelope:
    """Request deletion of the authenticated principal's local data."""
    return unavailable()
