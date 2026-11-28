from mcp.server import MCPServer

from .confirm_execute_playlist import confirm_execute_playlist
from .delete_data import delete_data
from .disconnect import disconnect
from .engagement_analysis import engagement_analysis
from .operation_status import operation_status
from .propose_playlist import propose_playlist
from .recommendations import recommendations
from .similar_channels import similar_channels
from .similar_videos import similar_videos

TOOLS = (
    similar_videos,
    similar_channels,
    recommendations,
    engagement_analysis,
    propose_playlist,
    confirm_execute_playlist,
    operation_status,
    disconnect,
    delete_data,
)


def register_tools(server: MCPServer[None]) -> None:
    for handler in TOOLS:
        server.add_tool(handler, structured_output=True)
