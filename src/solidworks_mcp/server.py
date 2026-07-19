"""SOLIDWORKS MCP Server 入口 (MCP 1.x API)"""

import sys
import asyncio
import functools
import concurrent.futures
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools import ALL_TOOLS

# 单线程 executor — 所有 COM 调用必须在同一条线程上，
# 因为 COM STA 模式下对象与创建它的线程绑定，跨线程访问会失败。
_com_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

# 注意: mcp 1.x 中 Server.list_tools/call_tool 是装饰器工厂，
# 必须用 @server.xxx() 注册 handler，子类重写方法不会生效。
server = Server("solidworks-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """返回所有可用工具"""
    return [
        Tool(
            name=t["name"],
            description=t["description"],
            inputSchema=t["inputSchema"],
        )
        for t in ALL_TOOLS
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """分发工具调用"""
    if arguments is None:
        arguments = {}

    for t in ALL_TOOLS:
        if t["name"] == name:
            try:
                # 所有 COM 调用通过单线程 executor 串行化，
                # 保证 COM STA 亲和性：连接、建模、查询都在同一条线程上
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    _com_executor,
                    functools.partial(t["handler"], **arguments),
                )
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                return [TextContent(type="text", text=f"[ERROR] 执行失败: {str(e)}")]

    return [TextContent(type="text", text=f"[ERROR] 未知工具: {name}")]


async def run():
    """以 stdio 模式运行"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
