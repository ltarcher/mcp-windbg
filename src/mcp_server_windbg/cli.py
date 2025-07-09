#!/usr/bin/env python3
"""
命令行界面模块，用于启动 MCP WinDBG 服务器。
提供本地模式（标准输入/输出）和远程模式（WebSocket）。
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Optional

from .server import serve
from .server_factory import ServerFactory


def setup_logging(verbose: bool = False) -> None:
    """设置日志级别和格式。
    
    Args:
        verbose: 是否启用详细日志
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]
    )


def parse_args() -> argparse.Namespace:
    """解析命令行参数。
    
    Returns:
        解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(
        description="MCP WinDBG Server - 用于分析 Windows 崩溃转储的 MCP 服务器"
    )
    
    # 通用选项
    parser.add_argument(
        "--cdb-path",
        help="cdb.exe 的自定义路径"
    )
    parser.add_argument(
        "--symbols-path",
        help="自定义符号路径"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="命令超时时间（秒）（默认：30）"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="启用详细输出"
    )
    
    # 服务器模式选项
    parser.add_argument(
        "--mode",
        choices=["local", "remote"],
        default="local",
        help="服务器模式：local（标准输入/输出）或 remote（WebSocket/SSE）（默认：local）"
    )
    
    # SSE服务器选项
    parser.add_argument(
        "--use-sse",
        action="store_true",
        help="在远程模式下使用SSE而不是WebSocket"
    )
    parser.add_argument(
        "--sse-port",
        type=int,
        default=8767,
        help="SSE服务器端口（默认：8767）"
    )
    
    # 远程模式选项
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="远程服务器主机（默认：0.0.0.0）"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket 服务器端口（默认：8765）"
    )
    parser.add_argument(
        "--upload-port",
        type=int,
        default=8766,
        help="文件上传服务器端口（默认：8766）"
    )
    parser.add_argument(
        "--upload-dir",
        default="./uploads",
        help="上传文件保存目录（默认：./uploads）"
    )
    
    return parser.parse_args()


async def main_async() -> None:
    """异步主函数，处理命令行参数并启动服务器。"""
    args = parse_args()
    setup_logging(args.verbose)
    
    # 获取符号路径（优先使用命令行参数，其次使用环境变量）
    symbols_path = args.symbols_path
    if not symbols_path and "_NT_SYMBOL_PATH" in os.environ:
        symbols_path = os.environ["_NT_SYMBOL_PATH"]
    
    if args.mode == "local":
        # 本地模式（标准输入/输出）
        logging.info("启动本地 MCP WinDBG 服务器（标准输入/输出模式）")
        await serve(
            cdb_path=args.cdb_path,
            symbols_path=symbols_path,
            timeout=args.timeout,
            verbose=args.verbose
        )
    else:
        # 远程模式（WebSocket）
        logging.info(f"启动远程 MCP WinDBG 服务器（WebSocket 模式）在 {args.host}:{args.port}")
        logging.info(f"文件上传服务器在 {args.host}:{args.upload_port}")
        
        # 确保上传目录存在
        os.makedirs(args.upload_dir, exist_ok=True)
        
        await ServerFactory.create_remote_server(
            host=args.host,
            port=args.port,
            upload_port=args.upload_port,
            upload_dir=args.upload_dir,
            cdb_path=args.cdb_path,
            symbols_path=symbols_path,
            timeout=args.timeout,
            verbose=args.verbose,
            use_sse=args.use_sse,
            sse_port=args.sse_port
        )


def main() -> None:
    """主入口点，启动异步事件循环。"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logging.info("收到中断信号，正在关闭服务器...")
    except Exception as e:
        logging.error(f"服务器错误: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()