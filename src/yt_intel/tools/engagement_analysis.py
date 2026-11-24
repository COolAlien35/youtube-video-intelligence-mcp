from .envelope import BoundPrincipal, ToolEnvelope, unavailable


async def engagement_analysis(
    metric: str, period: str, *, principal: BoundPrincipal
) -> ToolEnvelope:
    """Describe engagement for the requested metric and period."""
    # TBC: accepted metric and period vocabulary awaits the feature contract.
    return unavailable()
