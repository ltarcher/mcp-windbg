from aiohttp import web
import os
import uuid
import traceback

async def handle_upload(request):
    """Handle file upload requests."""
    try:
        reader = await request.multipart()
        field = await reader.next()
        
        if field is None or field.name != "file":
            return web.Response(status=400, text="Expected field 'file'")
        
        # 生成唯一文件名，保留原始扩展名
        original_filename = field.filename
        extension = os.path.splitext(original_filename)[1] if original_filename else ".dmp"
        if not extension:
            extension = ".dmp"
        
        filename = str(uuid.uuid4()) + extension
        upload_dir = request.app["upload_dir"]
        file_path = os.path.join(upload_dir, filename)
        
        # 保存上传的文件
        with open(file_path, 'wb') as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                f.write(chunk)
        
        return web.json_response({
            "success": True,
            "file_path": file_path,
            "original_filename": original_filename,
            "saved_filename": filename
        })
    except Exception as e:
        return web.json_response({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status=500)

async def start_upload_server(host="0.0.0.0", port=8766, upload_dir="./uploads"):
    """Start the file upload server.
    
    Args:
        host: Host to bind the server to
        port: Port to bind the server to
        upload_dir: Directory to save uploaded files
        
    Returns:
        The aiohttp AppRunner instance
    """
    # 确保上传目录存在
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    app = web.Application()
    app["upload_dir"] = upload_dir
    app.router.add_post("/upload", handle_upload)
    
    # 添加一个简单的状态检查端点
    async def health_check(request):
        return web.json_response({"status": "ok"})
    
    app.router.add_get("/health", health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    print(f"File upload server started at http://{host}:{port}/upload")
    print(f"Health check available at http://{host}:{port}/health")
    return runner