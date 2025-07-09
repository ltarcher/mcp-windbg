#!/usr/bin/env python3
"""
WebSocket客户端示例，用于连接到MCP WinDBG远程服务器。
此示例演示如何使用WebSocket连接到远程MCP WinDBG服务器，并执行各种操作。
"""

import asyncio
import json
import sys
import os
import websockets
import argparse
import uuid
import aiohttp
import mimetypes
from pathlib import Path

class MCPWinDbgClient:
    """MCP WinDBG WebSocket客户端"""
    
    def __init__(self, server_url="ws://localhost:8765", upload_url="http://localhost:8766/upload"):
        """初始化客户端
        
        Args:
            server_url: WebSocket服务器URL
            upload_url: 文件上传服务器URL
        """
        self.server_url = server_url
        self.upload_url = upload_url
        self.websocket = None
        self.request_id = 0
    
    async def connect(self):
        """连接到WebSocket服务器"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"已连接到 {self.server_url}")
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    async def close(self):
        """关闭WebSocket连接"""
        if self.websocket:
            await self.websocket.close()
            print("连接已关闭")
    
    async def list_tools(self):
        """获取可用工具列表"""
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "method": "list_tools",
            "params": {},
            "id": request_id
        }
        
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def call_tool(self, tool_name, arguments):
        """调用工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "method": "call_tool",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": request_id
        }
        
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def upload_file(self, file_path):
        """上传文件
        
        Args:
            file_path: 要上传的文件路径
            
        Returns:
            上传结果
        """
        if not os.path.exists(file_path):
            return {"success": False, "error": f"文件不存在: {file_path}"}
        
        try:
            # 确定文件的MIME类型
            content_type = mimetypes.guess_type(file_path)[0]
            if not content_type:
                content_type = 'application/octet-stream'
            
            # 准备表单数据
            data = aiohttp.FormData()
            data.add_field('file',
                          open(file_path, 'rb'),
                          filename=os.path.basename(file_path),
                          content_type=content_type)
            
            # 发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post(self.upload_url, data=data) as response:
                    result = await response.json()
                    return result
        except Exception as e:
            return {"success": False, "error": str(e)}

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP WinDBG WebSocket客户端示例")
    parser.add_argument("--server", default="ws://localhost:8765", help="WebSocket服务器URL")
    parser.add_argument("--upload", default="http://localhost:8766/upload", help="文件上传服务器URL")
    parser.add_argument("--dump", help="要分析的崩溃转储文件路径")
    parser.add_argument("--command", help="要执行的WinDBG命令")
    parser.add_argument("--list-tools", action="store_true", help="列出可用工具")
    parser.add_argument("--list-dumps", action="store_true", help="列出可用的崩溃转储文件")
    parser.add_argument("--upload-file", help="要上传的文件路径")
    
    args = parser.parse_args()
    
    client = MCPWinDbgClient(args.server, args.upload)
    if not await client.connect():
        return
    
    try:
        if args.list_tools:
            # 列出可用工具
            response = await client.list_tools()
            print("\n可用工具:")
            for tool in response.get("result", {}).get("tools", []):
                print(f"- {tool['name']}: {tool['description'].strip()}")
        
        elif args.list_dumps:
            # 列出可用的崩溃转储文件
            response = await client.call_tool("list_windbg_dumps", {})
            print("\n可用的崩溃转储文件:")
            print(response.get("result", {}).get("content", [{}])[0].get("text", "无结果"))
        
        elif args.upload_file:
            # 上传文件
            print(f"正在上传文件: {args.upload_file}")
            result = await client.upload_file(args.upload_file)
            if result.get("success"):
                print(f"文件上传成功: {result.get('saved_filename')}")
                print(f"文件路径: {result.get('file_path')}")
            else:
                print(f"文件上传失败: {result.get('error')}")
        
        elif args.dump:
            # 分析崩溃转储文件
            if args.command:
                # 执行特定命令
                print(f"在 {args.dump} 上执行命令: {args.command}")
                response = await client.call_tool("run_windbg_cmd", {
                    "dump_path": args.dump,
                    "command": args.command
                })
                print("\n命令结果:")
                print(response.get("result", {}).get("content", [{}])[0].get("text", "无结果"))
            else:
                # 执行默认分析
                print(f"分析崩溃转储文件: {args.dump}")
                response = await client.call_tool("open_windbg_dump", {
                    "dump_path": args.dump,
                    "include_stack_trace": True,
                    "include_modules": True,
                    "include_threads": True
                })
                print("\n分析结果:")
                print(response.get("result", {}).get("content", [{}])[0].get("text", "无结果"))
        
        else:
            print("请指定要执行的操作。使用 --help 查看可用选项。")
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())