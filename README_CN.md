# MCP WinDBG Server

MCP WinDBG Server 是一个基于 Model Context Protocol (MCP) 的服务器，它允许 AI 模型通过 WinDBG/CDB 分析 Windows 崩溃转储文件。该服务器提供了两种运行模式：本地模式（通过标准输入/输出通信）和远程模式（通过 WebSocket 通信）。

## 概述

这个 MCP 服务器与 [CDB](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/opening-a-crash-dump-file-using-cdb) 集成，使 AI 模型能够分析 Windows 崩溃转储。

## 简要说明

### 这是什么？

- 主要是一个使 AI 能够与 WinDBG 交互的工具。
- 整个"魔法"在于赋予 LLMs 执行调试器命令的能力。创造性地使用，这非常强大并能显著提高生产力。

这意味着，这是：

- 连接 LLMs（AI）与 WinDBG（CDB）的桥梁，用于辅助崩溃转储分析。
- 获取即时一级分类分析的方法，适用于对崩溃转储进行分类或自动分析简单案例。
- 基于自然语言的"氛围"分析平台，允许您要求 LLM 检查特定区域：
  - 示例：
    - "使用 `k` 显示调用堆栈并解释是什么可能导致这个访问违规"
    - "执行 `!peb` 并告诉我是否有可能影响这次崩溃的环境变量"
    - "检查第 3 帧并分析传递给这个函数的参数"
    - "对这个对象使用 `dx -r2` 并解释其状态"（相当于 `dx -r2 ((MyClass*)0x12345678)`）
    - "使用 `!heap -p -a 0xABCD1234` 分析这个堆地址并检查缓冲区溢出"
    - "运行 `.ecxr` 后跟 `k` 并解释异常的根本原因"
    - "使用 `!runaway` 和 `!threads` 检查线程池中的计时问题"
    - "使用 `db/dw/dd` 检查此地址周围的内存以识别损坏模式"
    - ...以及基于您特定崩溃场景的许多其他分析方法

### 这不是什么？

- 自动修复所有问题的神奇解决方案。
- 具有自定义 AI 的全功能产品。相反，它是一个**围绕 CDB 的简单 Python 包装器**，**依赖于 LLM 的 WinDBG 专业知识**，最好与您自己的领域知识相结合。

## 功能特点

- 分析 Windows 崩溃转储文件
- 执行 WinDBG/CDB 命令
- 列出可用的崩溃转储文件
- 支持本地和远程操作模式
- 远程模式支持文件上传功能

## 安装

```bash
pip install mcp-windbg
```

## 先决条件

- Python 3.7 或更高版本
- 安装了**Windows 调试工具**的 Windows 操作系统。
  - 这是 [Windows SDK](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/) 的一部分。
- 支持 Model Context Protocol 的 LLM。
  - 已通过 GitHub Copilot 测试了 Claude 3.7 Sonnet，对结果非常满意。
  - 对于 GitHub Copilot，需要启用 Chat 功能中的 Model Context Protocol。
  - 参见 [使用 Model Context Protocol (MCP) 扩展 Copilot Chat](https://docs.github.com/en/copilot/customizing-copilot/extending-copilot-chat-with-mcp)。

## 使用方法

### 本地模式（默认）

本地模式通过标准输入/输出与 MCP 客户端通信，适用于直接集成到支持 MCP 的应用程序中。

```bash
mcp-windbg
```

### 远程模式

远程模式启动一个 WebSocket 服务器，允许通过网络连接访问 WinDBG 功能。这种模式还包括一个文件上传服务器，方便上传崩溃转储文件。

```bash
mcp-windbg --mode remote --host 0.0.0.0 --port 8765 --upload-port 8766 --upload-dir ./uploads
```

### 命令行选项

```
--cdb-path PATH       自定义 cdb.exe 路径
--symbols-path PATH   自定义符号路径
--timeout SECONDS     命令超时时间（秒），默认为 30
--verbose             启用详细输出
--mode {local,remote} 服务器模式：local（标准输入/输出）或 remote（WebSocket），默认为 local
--host HOST           远程服务器主机，默认为 0.0.0.0
--port PORT           WebSocket 服务器端口，默认为 8765
--upload-port PORT    文件上传服务器端口，默认为 8766
--upload-dir DIR      上传文件保存目录，默认为 ./uploads
```

## 与 VS Code 集成

要将此 MCP 服务器与 Visual Studio Code 集成：

1. 在您的工作区中创建一个 `.vscode/mcp.json` 文件，包含以下配置：

```json
{
    "servers": {
        "mcp_server_windbg": {
            "type": "stdio",
            "command": "${workspaceFolder}/.venv/Scripts/python",
            "args": [
                "-m",
                "mcp_server_windbg"
            ],
            "env": {
                "_NT_SYMBOL_PATH": "SRV*C:\\Symbols*https://msdl.microsoft.com/download/symbols"
            }
        },
    }
}
```

或者，编辑您的用户设置以全局启用它（独立于工作区）。
添加后，并启用 Chat 功能中的 Model Context Protocol，此模型上下文协议服务器的工具将在 Agent 模式下可用。

它应该看起来像这样：

![Visual Studio Code 集成](./images/vscode-integration.png)

## 示例客户端

项目包含两个示例客户端，用于演示如何与远程模式的 MCP WinDBG 服务器交互：

### Python WebSocket 客户端

`examples/websocket_client.py` 是一个命令行 Python 客户端，可以连接到远程 MCP WinDBG 服务器并执行各种操作。

```bash
# 列出可用工具
python examples/websocket_client.py --list-tools

# 列出可用的崩溃转储文件
python examples/websocket_client.py --list-dumps

# 上传崩溃转储文件
python examples/websocket_client.py --upload-file path/to/crash.dmp

# 分析崩溃转储文件
python examples/websocket_client.py --dump path/to/crash.dmp

# 在崩溃转储上执行特定命令
python examples/websocket_client.py --dump path/to/crash.dmp --command "!analyze -v"
```

### Web 客户端

`examples/web_client.html` 是一个基于浏览器的客户端，提供了图形界面来与远程 MCP WinDBG 服务器交互。

要使用 Web 客户端：
1. 启动 MCP WinDBG 服务器的远程模式
2. 在浏览器中打开 `examples/web_client.html` 文件
3. 输入服务器 URL 并连接
4. 使用界面执行各种操作

## 工具说明

MCP WinDBG 服务器提供以下工具：

### open_windbg_dump

分析 Windows 崩溃转储文件，执行常见的 WinDBG 命令并返回结果。

参数：
- `dump_path`：崩溃转储文件路径
- `include_stack_trace`：是否包含堆栈跟踪（可选，默认为 false）
- `include_modules`：是否包含已加载模块列表（可选，默认为 false）
- `include_threads`：是否包含线程信息（可选，默认为 false）

### run_windbg_cmd

在已加载的崩溃转储上执行特定的 WinDBG 命令。

参数：
- `dump_path`：崩溃转储文件路径
- `command`：要执行的 WinDBG 命令

### close_windbg_dump

卸载崩溃转储并释放资源。

参数：
- `dump_path`：要卸载的崩溃转储文件路径

### list_windbg_dumps

列出指定目录中的 Windows 崩溃转储文件。

参数：
- `directory`：要搜索的目录路径（可选，默认为系统崩溃转储目录）

## 开发设置

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/mcp-windbg.git
cd mcp-windbg
```

2. 创建并激活虚拟环境：

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

3. 以开发模式安装包：

```bash
pip install -e .
```

4. 安装测试依赖：

```bash
pip install -e ".[test]"
```

## 故障排除

### 找不到 CDB

如果您收到"CDB executable not found"错误，请确保：

1. 您的系统上已安装 WinDBG/CDB
2. CDB 可执行文件在您的系统 PATH 中，或者
3. 您使用 `--cdb-path` 选项指定路径

### 符号路径问题

为了正确分析崩溃，设置您的符号路径：

1. 使用 `--symbols-path` 参数，或
2. 设置 `_NT_SYMBOL_PATH` 环境变量

### 常用符号路径

```
SRV*C:\Symbols*https://msdl.microsoft.com/download/symbols
```

## 许可证

MIT