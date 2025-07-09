from .server import serve
from .server_factory import ServerFactory

def main():
    """MCP WinDBG Server - Windows crash dump analysis functionality for MCP"""
    import argparse
    import asyncio
    import os

    parser = argparse.ArgumentParser(
        description="Give a model the ability to analyze Windows crash dumps with WinDBG/CDB"
    )
    parser.add_argument("--cdb-path", type=str, help="Custom path to cdb.exe")
    parser.add_argument("--symbols-path", type=str, help="Custom symbols path")
    parser.add_argument("--timeout", type=int, default=30, help="Command timeout in seconds")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    # 新增参数
    parser.add_argument("--mode", choices=["local", "remote"], default="local",
                        help="Server mode: local (stdio) or remote (WebSocket)")
    parser.add_argument("--host", default="0.0.0.0", help="Host for remote server")
    parser.add_argument("--port", type=int, default=8765, help="Port for WebSocket server")
    parser.add_argument("--upload-port", type=int, default=8766, help="Port for file upload server")
    parser.add_argument("--upload-dir", default="./uploads", help="Directory for uploaded files")

    args = parser.parse_args()
    
    if args.mode == "local":
        # 本地模式，使用stdio服务器
        asyncio.run(serve(
            cdb_path=args.cdb_path,
            symbols_path=args.symbols_path,
            timeout=args.timeout,
            verbose=args.verbose
        ))
    else:
        # 远程模式，启动WebSocket服务器和文件上传服务器
        # 确保上传目录是绝对路径
        upload_dir = os.path.abspath(args.upload_dir)
        
        asyncio.run(ServerFactory.create_remote_server(
            host=args.host,
            port=args.port,
            upload_port=args.upload_port,
            upload_dir=upload_dir,
            cdb_path=args.cdb_path,
            symbols_path=args.symbols_path,
            timeout=args.timeout,
            verbose=args.verbose
        ))


if __name__ == "__main__":
    main()