# WinDbg MCP SSE 服务器

## 简介

SSE（Server-Sent Events）服务器是 WinDbg MCP 服务器的一个扩展功能，它允许通过浏览器访问和控制 WinDbg 调试器。SSE 服务器提供了一个基于 Web 的界面，可以执行调试命令、调用工具和查看调试输出。

## 功能特点

- 基于浏览器的调试器控制界面
- 实时显示调试输出
- 支持执行调试命令
- 支持调用 MCP 工具
- 支持查看进程、模块和线程列表

## 使用方法

### 启动服务器

可以通过命令行参数 `--use-sse` 和 `--sse-port` 启用 SSE 服务器：

```bash
python -m mcp_server_windbg --mode remote --use-sse --sse-port 8767
```

或者使用测试脚本：

```bash
python test_sse_server.py --cdb-path "C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe" --symbols-path "srv*c:\symbols*https://msdl.microsoft.com/download/symbols"
```

### 访问 Web 界面

启动服务器后，在浏览器中访问：

```
http://localhost:8767
```

浏览器将自动重定向到 SSE 客户端页面。

### 使用 Web 界面

1. 连接到 SSE 服务器：
   - 确认 SSE 服务器 URL 正确（默认为 `http://localhost:8767/events`）
   - 点击"连接"按钮

2. 执行调试命令：
   - 在命令输入框中输入调试命令
   - 点击"发送"按钮或按回车键

3. 调用工具：
   - 在工具名称输入框中输入工具名称
   - 在参数输入框中输入 JSON 格式的参数（可选）
   - 点击"调用工具"按钮

4. 使用快捷工具按钮：
   - 点击"列出工具"按钮查看可用工具
   - 点击"列出资源"按钮查看可用资源
   - 点击"进程列表"、"模块列表"或"线程列表"按钮查看相应信息

5. 查看输出：
   - 所有命令和响应都会显示在右侧的消息日志区域
   - 可以点击"清除日志"按钮清除日志

## 技术说明

SSE 服务器基于 aiohttp 实现，它使用 Server-Sent Events 技术向浏览器推送调试器输出，并通过 HTTP POST 请求接收命令和工具调用。

SSE 服务器与 WebSocket 服务器并行运行，它们共享相同的调试器实例，因此可以同时使用 WebSocket 客户端和 SSE 客户端控制调试器。

## 注意事项

- SSE 服务器默认监听 8767 端口，可以通过 `--sse-port` 参数修改
- 确保防火墙允许访问 SSE 服务器端口
- 为了安全起见，建议只在本地网络中使用 SSE 服务器