from .envelope import BoundPrincipal, ToolEnvelope, unavailable


async def disconnect(account_ref: str, *, principal: BoundPrincipal) -> ToolEnvelope:
    """Disconnect a linked Google account."""
    return unavailable()
