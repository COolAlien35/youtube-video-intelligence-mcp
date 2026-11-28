from .envelope import BoundPrincipal, ToolEnvelope, unavailable


async def operation_status(operation_id: str, *, principal: BoundPrincipal) -> ToolEnvelope:
    """Read the status of a principal-scoped playlist operation."""
    return unavailable()
