"""
SSE服务器模块，用于通过Server-Sent Events提供MCP服务器功能。
"""

import asyncio
import json
import logging
from typing import Dict, Any, Tuple, Optional, List, Set
import uuid
import os
import pathlib

from aiohttp import web
from aiohttp.web import Request, Response, Application, AppRunner, TCPSite

from modelcontextprotocol.server import Server
from modelcontextprotocol.types import (
    JsonRpcRequest, JsonRpcResponse, JsonRpcError,
    ErrorCode
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SSEServer:
    """SSE服务器类，用于通过Server-Sent Events提供MCP服务器功能。"""
    
    def __init__(self, app: Application, mcp_server: Server):
        """初始化SSE服务器。
        
        Args:
            app: aiohttp应用实例
            mcp_server: MCP服务器实例
        """
        self.app = app
        self.mcp_server = mcp_server
        self.clients: Dict[str, web.StreamResponse] = {}
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.response_tasks: Dict[str, asyncio.Task] = {}
        
        # 设置路由
        self.app.router.add_get('/events', self.events_handler)
        self.app.router.add_post('/request', self.request_handler)
        self.app.router.add_get('/', self.index_handler)
        
        # 设置静态文件路由
        static_path = pathlib.Path(__file__).parent / "static"
        self.app.router.add_static('/static', static_path)
        
        # 启动请求处理任务
        self.request_processor_task = asyncio.create_task(self.process_requests())
    
    @classmethod
    async def create(cls, server_instance: Server, host: str = "0.0.0.0", port: int = 8767) -> Tuple['SSEServer', AppRunner]:
        """创建并启动SSE服务器。
        
        Args:
            server_instance: MCP服务器实例
            host: 主机地址
            port: 端口号
            
        Returns:
            SSE服务器实例和aiohttp运行器
        """
        app = web.Application()
        server = cls(app, server_instance)
        
        # 启动服务器
        runner = web.AppRunner(app)
        await runner.setup()
        site = TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"SSE服务器已启动，监听地址: http://{host}:{port}")
        logger.info(f"SSE客户端页面可通过 http://{host}:{port} 访问")
        
        return server, runner
    
    async def index_handler(self, request: Request) -> Response:
        """处理根路径请求，返回SSE客户端HTML页面。
        
        Args:
            request: HTTP请求
            
        Returns:
            HTTP响应
        """
        # 重定向到SSE客户端页面
        return web.HTTPFound('/static/sse_client.html')
    
    async def events_handler(self, request: Request) -> Response:
        """处理SSE事件流请求。
        
        Args:
            request: HTTP请求
            
        Returns:
            SSE事件流响应
        """
        # 创建SSE响应
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        response.headers['Access-Control-Allow-Origin'] = '*'
        await response.prepare(request)
        
        # 生成客户端ID并存储响应对象
        client_id = str(uuid.uuid4())
        self.clients[client_id] = response
        
        # 发送连接成功消息
        await self.send_event(response, {
            "type": "connection",
            "status": "connected",
            "client_id": client_id
        })
        
        try:
            # 保持连接直到客户端断开
            while True:
                await asyncio.sleep(30)
                # 发送心跳消息
                await self.send_event(response, {"type": "heartbeat"})
        except ConnectionResetError:
            logger.info(f"客户端 {client_id} 断开连接")
        finally:
            # 清理客户端连接
            if client_id in self.clients:
                del self.clients[client_id]
        
        return response
    
    async def request_handler(self, request: Request) -> Response:
        """处理JSON-RPC请求。
        
        Args:
            request: HTTP请求
            
        Returns:
            HTTP响应
        """
        try:
            # 解析请求体
            data = await request.json()
            
            # 验证JSON-RPC请求
            if not isinstance(data, dict) or 'jsonrpc' not in data or data['jsonrpc'] != '2.0':
                return web.json_response({"error": "Invalid JSON-RPC request"}, status=400)
            
            # 将请求放入队列
            await self.request_queue.put(data)
            
            # 返回成功响应
            return web.json_response({"status": "request_accepted"})
            
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f"处理请求时出错: {str(e)}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def send_event(self, response: web.StreamResponse, data: Dict[str, Any]) -> None:
        """向客户端发送SSE事件。
        
        Args:
            response: 流响应对象
            data: 要发送的数据
        """
        try:
            await response.write(f"data: {json.dumps(data)}\n\n".encode('utf-8'))
            await response.drain()
        except ConnectionResetError:
            # 客户端已断开连接
            pass
        except Exception as e:
            logger.error(f"发送事件时出错: {str(e)}")
    
    async def broadcast_event(self, data: Dict[str, Any]) -> None:
        """向所有连接的客户端广播事件。
        
        Args:
            data: 要广播的数据
        """
        disconnected_clients = []
        
        for client_id, response in self.clients.items():
            try:
                await self.send_event(response, data)
            except Exception:
                # 标记断开连接的客户端
                disconnected_clients.append(client_id)
        
        # 清理断开连接的客户端
        for client_id in disconnected_clients:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def process_requests(self) -> None:
        """处理请求队列中的请求。"""
        while True:
            try:
                # 从队列中获取请求
                request_data = await self.request_queue.get()
                
                # 处理请求
                response_data = await self.handle_request(request_data)
                
                # 广播响应
                await self.broadcast_event(response_data)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"处理请求队列时出错: {str(e)}")
                # 广播错误
                await self.broadcast_event({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"内部错误: {str(e)}"
                    },
                    "id": None
                })
    
    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个JSON-RPC请求。
        
        Args:
            request_data: JSON-RPC请求数据
            
        Returns:
            JSON-RPC响应数据
        """
        request_id = request_data.get('id')
        method = request_data.get('method')
        params = request_data.get('params', {})
        
        try:
            # 创建JSON-RPC请求对象
            request = JsonRpcRequest(
                jsonrpc="2.0",
                method=method,
                params=params,
                id=request_id
            )
            
            # 处理请求
            if method == 'execute_command':
                response = await self.mcp_server.handle_execute_command(request)
            elif method == 'call_tool':
                response = await self.mcp_server.handle_call_tool(request)
            elif method == 'list_tools':
                response = await self.mcp_server.handle_list_tools(request)
            elif method == 'list_resources':
                response = await self.mcp_server.handle_list_resources(request)
            else:
                # 未知方法
                response = JsonRpcResponse(
                    jsonrpc="2.0",
                    error=JsonRpcError(
                        code=ErrorCode.MethodNotFound,
                        message=f"未知方法: {method}"
                    ),
                    id=request_id
                )
            
            # 返回响应
            return response.dict()
            
        except Exception as e:
            logger.error(f"处理请求时出错: {str(e)}")
            # 返回错误响应
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"内部错误: {str(e)}"
                },
                "id": request_id
            }
    
    async def close(self) -> None:
        """关闭SSE服务器。"""
        # 取消请求处理任务
        if hasattr(self, 'request_processor_task'):
            self.request_processor_task.cancel()
            try:
                await self.request_processor_task
            except asyncio.CancelledError:
                pass
        
        # 关闭所有客户端连接
        for client_id, response in list(self.clients.items()):
            try:
                await response.write(b"event: close\ndata: {\"reason\": \"server_shutdown\"}\n\n")
                await response.write_eof()
            except Exception:
                pass
        
        self.clients.clear()