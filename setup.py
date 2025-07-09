from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mcp-windbg",
    version="0.1.0",
    author="MCP WinDBG Team",
    author_email="example@example.com",
    description="MCP server for WinDBG/CDB crash dump analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/mcp-windbg",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/mcp-windbg/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Debuggers",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={
        "mcp_server_windbg": ["static/*"],
    },
    python_requires=">=3.7",
    install_requires=[
        "mcp>=0.1.0",
        "pydantic>=2.0.0",
        "websockets>=10.0",
        "aiohttp>=3.8.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-windbg=mcp_server_windbg.cli:main",
        ],
    },
)