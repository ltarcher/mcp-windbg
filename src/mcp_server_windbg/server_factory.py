import asyncio
import os
import traceback
import glob
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INVALID_PARAMS, INTERNAL_ERROR

from .server import serve as serve_stdio
from .server import (
    get_or_create_session, 
    unload_session, 
    get_local_dumps_path,
    OpenWindbgDump,
    RunWindbgCmdParams,
    CloseWindbgDumpParams,
    ListWindbgDumpsParams
)
from .websocket_server import start_websocket_server
from .file_upload import start_upload_server

class ServerFactory:
    """Factory for creating MCP servers."""
    
    @staticmethod
    async def create_local_server(
        cdb_path: Optional[str] = None,
        symbols_path: Optional[str] = None,
        timeout: int = 30,
        verbose: bool = False
    ) -> None:
        """Create a local stdio-based MCP server.
        
        Args:
            cdb_path: Optional custom path to cdb.exe
            symbols_path: Optional custom symbols path
            timeout: Command timeout in seconds
            verbose: Whether to enable verbose output
        """
        await serve_stdio(
            cdb_path=cdb_path,
            symbols_path=symbols_path,
            timeout=timeout,
            verbose=verbose
        )
    
    @staticmethod
    async def create_remote_server(
        host: str = "0.0.0.0",
        port: int = 8765,
        upload_port: int = 8766,
        upload_dir: str = "./uploads",
        cdb_path: Optional[str] = None,
        symbols_path: Optional[str] = None,
        timeout: int = 30,
        verbose: bool = False
    ) -> None:
        """Create a remote WebSocket-based MCP server with file upload capability.
        
        Args:
            host: Host to bind the server to
            port: Port for the WebSocket server
            upload_port: Port for the file upload server
            upload_dir: Directory to save uploaded files
            cdb_path: Optional custom path to cdb.exe
            symbols_path: Optional custom symbols path
            timeout: Command timeout in seconds
            verbose: Whether to enable verbose output
        """
        # 创建MCP服务器实例
        server = Server("mcp-windbg")
        
        # 实现list_tools处理函数
        async def list_tools_handler() -> List[Tool]:
            return [
                Tool(
                    name="open_windbg_dump",
                    description="""
                    Analyze a Windows crash dump file using WinDBG/CDB.
                    This tool executes common WinDBG commands to analyze the crash dump and returns the results.
                    """,
                    inputSchema=OpenWindbgDump.model_json_schema(),
                ),
                Tool(
                    name="run_windbg_cmd",
                    description="""
                    Execute a specific WinDBG command on a loaded crash dump.
                    This tool allows you to run any WinDBG command on the crash dump and get the output.
                    """,
                    inputSchema=RunWindbgCmdParams.model_json_schema(),
                ),
                Tool(
                    name="close_windbg_dump",
                    description="""
                    Unload a crash dump and release resources.
                    Use this tool when you're done analyzing a crash dump to free up resources.
                    """,
                    inputSchema=CloseWindbgDumpParams.model_json_schema(),
                ),
                Tool(
                    name="list_windbg_dumps",
                    description="""
                    List Windows crash dump files in the specified directory.
                    This tool helps you discover available crash dumps that can be analyzed.
                    """,
                    inputSchema=ListWindbgDumpsParams.model_json_schema(),
                )
            ]
        
        # 实现call_tool处理函数
        async def call_tool_handler(name: str, arguments: dict) -> List[TextContent]:
            try:
                if name == "open_windbg_dump":
                    # Check if dump_path is missing or empty
                    if "dump_path" not in arguments or not arguments.get("dump_path"):
                        local_dumps_path = get_local_dumps_path()
                        dumps_found_text = ""
                        
                        if local_dumps_path:
                            # Find dump files in the local dumps directory
                            search_pattern = os.path.join(local_dumps_path, "*.*dmp")
                            dump_files = glob.glob(search_pattern)
                            
                            if dump_files:
                                dumps_found_text = f"\n\nI found {len(dump_files)} crash dump(s) in {local_dumps_path}:\n\n"
                                for i, dump_file in enumerate(dump_files[:10]):  # Limit to 10 dumps to avoid clutter
                                    try:
                                        size_mb = round(os.path.getsize(dump_file) / (1024 * 1024), 2)
                                    except (OSError, IOError):
                                        size_mb = "unknown"
                                    
                                    dumps_found_text += f"{i+1}. {dump_file} ({size_mb} MB)\n"
                                    
                                if len(dump_files) > 10:
                                    dumps_found_text += f"\n... and {len(dump_files) - 10} more dump files.\n"
                                    
                                dumps_found_text += "\nYou can analyze one of these dumps by specifying its path."
                        
                        return [TextContent(
                            type="text",
                            text=f"Please provide a path to a crash dump file to analyze.{dumps_found_text}\n\n"
                                f"You can use the 'list_windbg_dumps' tool to discover available crash dumps."
                        )]
                    
                    args = OpenWindbgDump(**arguments)
                    session = get_or_create_session(
                        args.dump_path, cdb_path, symbols_path, timeout, verbose
                    )
                    
                    results = []
                    
                    crash_info = session.send_command(".lastevent")
                    results.append("### Crash Information\n```\n" + "\n".join(crash_info) + "\n```\n\n")
                    
                    # Run !analyze -v
                    analysis = session.send_command("!analyze -v")
                    results.append("### Crash Analysis\n```\n" + "\n".join(analysis) + "\n```\n\n")
                    
                    # Optional
                    if args.include_stack_trace:
                        stack = session.send_command("kb")
                        results.append("### Stack Trace\n```\n" + "\n".join(stack) + "\n```\n\n")
                    
                    if args.include_modules:
                        modules = session.send_command("lm")
                        results.append("### Loaded Modules\n```\n" + "\n".join(modules) + "\n```\n\n")
                    
                    if args.include_threads:
                        threads = session.send_command("~")
                        results.append("### Threads\n```\n" + "\n".join(threads) + "\n```\n\n")
                    
                    return [TextContent(
                        type="text",
                        text="".join(results)
                    )]
                    
                elif name == "run_windbg_cmd":
                    args = RunWindbgCmdParams(**arguments)
                    session = get_or_create_session(
                        args.dump_path, cdb_path, symbols_path, timeout, verbose
                    )
                    
                    output = session.send_command(args.command)
                    
                    return [TextContent(
                        type="text",
                        text=f"### Command: {args.command}\n```\n" + "\n".join(output) + "\n```"
                    )]
                    
                elif name == "close_windbg_dump":
                    args = CloseWindbgDumpParams(**arguments)
                    unload_session(args.dump_path)
                    
                    return [TextContent(
                        type="text",
                        text=f"Crash dump {args.dump_path} has been unloaded."
                    )]
                    
                elif name == "list_windbg_dumps":
                    args = ListWindbgDumpsParams(**arguments)
                    
                    # Use provided directory or default
                    search_dir = args.directory if args.directory else get_local_dumps_path()
                    
                    if not search_dir:
                        return [TextContent(
                            type="text",
                            text="No directory specified and no default dumps directory found."
                        )]
                    
                    # Find dump files
                    search_pattern = os.path.join(search_dir, "*.*dmp")
                    dump_files = glob.glob(search_pattern)
                    
                    if not dump_files:
                        return [TextContent(
                            type="text",
                            text=f"No crash dump files found in {search_dir}"
                        )]
                    
                    # Format results
                    result_text = f"Found {len(dump_files)} crash dump(s) in {search_dir}:\n\n"
                    
                    for i, dump_file in enumerate(dump_files):
                        try:
                            size_mb = round(os.path.getsize(dump_file) / (1024 * 1024), 2)
                            modified_time = os.path.getmtime(dump_file)
                            modified_str = datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
                        except (OSError, IOError):
                            size_mb = "unknown"
                            modified_str = "unknown"
                        
                        result_text += f"{i+1}. {dump_file} ({size_mb} MB, modified: {modified_str})\n"
                    
                    return [TextContent(
                        type="text",
                        text=result_text
                    )]
                    
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
                    
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}\n\nTraceback: {traceback.format_exc()}"
                )]
        
        # 设置处理函数
        server.list_tools_handler = list_tools_handler
        server.call_tool_handler = call_tool_handler
        
        # 启动文件上传服务器
        upload_runner = await start_upload_server(
            host=host,
            port=upload_port,
            upload_dir=upload_dir
        )
        
        # 启动WebSocket服务器
        await start_websocket_server(
            server_instance=server,
            host=host,
            port=port
        )