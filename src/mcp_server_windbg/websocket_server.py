import asyncio
import json
import traceback
import websockets
from typing import Dict, Any, List
from mcp.types import TextContent

async def websocket_handler(websocket, path, server_instance):
    """Handle WebSocket connections and process MCP messages."""
    async for message in websocket:
        try:
            request = json.loads(message)
            # 处理MCP请求
            if request.get("type") == "list_tools":
                tools = await server_instance.list_tools_handler()
                await websocket.send(json.dumps({
                    "type": "tools", 
                    "tools": [tool.model_dump() for tool in tools]
                }))
            elif request.get("type") == "call_tool":
                name = request.get("name")
                arguments = request.get("arguments", {})
                result = await server_instance.call_tool_handler(name, arguments)
                await websocket.send(json.dumps({
                    "type": "result", 
                    "result": [content.model_dump() for content in result]
                }))
            else:
                await websocket.send(json.dumps({
                    "type": "error", 
                    "error": f"Unknown request type: {request.get('type')}"
                }))
        except Exception as e:
            await websocket.send(json.dumps({
                "type": "error", 
                "error": str(e),
                "traceback": traceback.format_exc()
            }))

async def start_websocket_server(
    server_instance,
    host: str = "0.0.0.0", 
    port: int = 8765
):
    """Start the WebSocket server.
    
    Args:
        server_instance: The MCP server instance
        host: Host to bind the server to
        port: Port to bind the server to
    """
    handler = lambda ws, path: websocket_handler(ws, path, server_instance)
    server = await websockets.serve(handler, host, port)
    print(f"WebSocket server started at ws://{host}:{port}")
    await server.wait_closed()