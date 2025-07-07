# MCP Server for WinDBG Crash Analysis

用于使用 WinDBG/CDB 分析 Windows 崩溃转储的 Model Context Protocol 服务器。

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

## 博客

我在博客中写了整个旅程。

- [崩溃分析的未来：AI 遇见 WinDBG](https://svnscha.de/posts/ai-meets-windbg/)

## 先决条件

- Python 3.10 或更高版本
- 安装了**Windows 调试工具**的 Windows 操作系统。
  - 这是 [Windows SDK](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/) 的一部分。
- 支持 Model Context Protocol 的 LLM。
    - 我已通过 GitHub Copilot 测试了 Claude 3.7 Sonnet，对结果非常满意。
  - 对于 GitHub Copilot，需要启用 Chat 功能中的 Model Context Protocol。
  - 参见 [使用 Model Context Protocol (MCP) 扩展 Copilot Chat](https://docs.github.com/en/copilot/customizing-copilot/extending-copilot-chat-with-mcp)。

## 开发设置

1. 克隆仓库：

```bash
git clone https://github.com/svnscha/mcp-windbg.git
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

## 使用方法

### 与 VS Code 集成

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

### 启动 MCP 服务器（可选）

如果通过 Copilot 集成，则不需要这个。IDE 将自动启动 MCP。

使用模块命令启动服务器：

```bash
python -m mcp_server_windbg
```

### 命令行选项

```bash
python -m mcp_server_windbg [options]
```

可用选项：

- `--cdb-path CDB_PATH`：cdb.exe 的自定义路径
- `--symbols-path SYMBOLS_PATH`：自定义符号路径
- `--timeout TIMEOUT`：命令超时时间（秒）（默认：30）
- `--verbose`：启用详细输出

2. 根据需要自定义配置：
   - 如有需要，调整 Python 解释器路径
   - 通过在 `args` 数组中添加 `"--cdb-path": "C:\\path\\to\\cdb.exe"` 来设置 CDB 的自定义路径
   - 如上所示设置符号路径环境变量，或将 `"--symbols-path"` 添加到参数中

### 与 Copilot 集成

一旦在 VS Code 中配置了服务器：

1. 在 Copilot 设置中启用 Chat 功能中的 MCP
2. MCP 服务器将出现在 Copilot 的可用工具中
3. WinDBG 分析功能将通过 Copilot 的界面访问
4. 您现在可以通过 Copilot 使用自然语言查询直接分析崩溃转储

## 工具

此服务器提供以下工具：

- `open_windbg_dump`：使用常见的 WinDBG 命令分析 Windows 崩溃转储文件
- `run_windbg_cmd`：在加载的崩溃转储上执行特定的 WinDBG 命令
- `list_windbg_dumps`：列出指定目录中的 Windows 崩溃转储（.dmp）文件
- `close_windbg_dump`：卸载崩溃转储并释放资源

## 运行测试

要运行测试：

```bash
pytest
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