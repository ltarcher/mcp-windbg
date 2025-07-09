"""
测试SSE服务器功能的脚本。
"""

import asyncio
import argparse
import logging
import os
import sys

from src.mcp_server_windbg import ServerFactory

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """主函数，启动SSE服务器。"""
    parser = argparse.ArgumentParser(description="测试SSE服务器功能")
    parser.add_argument("--host", default="localhost", help="主机地址")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket服务器端口")
    parser.add_argument("--sse-port", type=int, default=8767, help="SSE服务器端口")
    parser.add_argument("--cdb-path", default="", help="CDB路径")
    parser.add_argument("--symbols-path", default="", help="符号路径")
    
    args = parser.parse_args()
    
    # 检查CDB路径
    cdb_path = args.cdb_path
    if not cdb_path:
        # 尝试从环境变量获取
        cdb_path = os.environ.get("CDB_PATH", "")
        if not cdb_path:
            logger.warning("未指定CDB路径，某些功能可能不可用")
    
    # 检查符号路径
    symbols_path = args.symbols_path
    if not symbols_path:
        # 尝试从环境变量获取
        symbols_path = os.environ.get("_NT_SYMBOL_PATH", "")
        if not symbols_path:
            logger.warning("未指定符号路径，某些功能可能不可用")
    
    try:
        # 启动远程服务器，启用SSE
        await ServerFactory.create_remote_server(
            host=args.host,
            port=args.port,
            upload_port=args.port + 1,
            upload_dir="./uploads",
            cdb_path=cdb_path,
            symbols_path=symbols_path,
            timeout=30,
            verbose=True,
            use_sse=True,
            sse_port=args.sse_port
        )
        
        # 保持服务器运行
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("服务器已停止")
    except Exception as e:
        logger.error(f"服务器运行出错: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))