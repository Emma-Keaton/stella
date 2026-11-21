from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

FEATURE_METADATA = {
    "name": "mcp_builder",
    "aliases": ["mcp", "model context protocol", "mcp server", "build mcp", "mcp tools", "mcp typescript", "mcp python", "fastmcp", "mcp sdk"],
    "description": "Build Model Context Protocol (MCP) servers to connect LLMs to external tools, APIs, and data sources. Supports TypeScript (SDK v2) and Python (FastMCP).",
    "triggers": ["mcp", "model context protocol", "mcp server", "build mcp", "mcp tools", "mcp typescript", "mcp python", "fastmcp", "mcp sdk"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "enum": ["create_server","add_tool","add_resource","add_prompt","generate_typescript","generate_python","validate_server","create_evaluation"]},
            "server_name": {"type": "STRING", "description": "Name of the MCP server"},
            "language": {"type": "STRING", "enum": ["typescript", "python"], "description": "Programming language"},
            "transport": {"type": "STRING", "enum": ["stdio", "streamable-http"], "description": "Transport protocol"},
            "tool_name": {"type": "STRING", "description": "Tool name"},
            "tool_description": {"type": "STRING", "description": "Tool description"},
            "tool_schema": {"type": "OBJECT", "description": "JSON Schema for tool parameters"},
            "resource_uri": {"type": "STRING", "description": "Resource URI template"},
            "resource_name": {"type": "STRING", "description": "Resource name"},
            "prompt_name": {"type": "STRING", "description": "Prompt name"},
            "prompt_description": {"type": "STRING", "description": "Prompt description"}
        },
        "required": ["operation"]
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": [],
}

API_SOURCES = {
    "mcp_spec": {"name": "MCP Specification", "url": "https://modelcontextprotocol.io", "auth_tier": "none"},
    "typescript_sdk": {"name": "TypeScript SDK v2", "url": "https://github.com/modelcontextprotocol/typescript-sdk", "auth_tier": "github"},
    "python_fastmcp": {"name": "Python FastMCP", "url": "https://github.com/jlowin/fastmcp", "auth_tier": "github"},
}

def _op_result(title: str, summary: str, ok: bool, operation: str, data: Dict = None, narrative: str = None) -> Dict:
    return {
        "title": title,
        "summary": summary[:200],
        "spoken_narrative": narrative or summary[:200],
        "ok": ok,
        "operation": operation,
        "record": {"ok": ok, "content": summary, "data": data or {}},
    }


TS_SERVER_TEMPLATE = '''import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

const server = new Server(
  { name: "{name}", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler("tools/list", async () => ({
  tools: [{
    name: "example_tool",
    description: "An example tool",
    inputSchema: z.object({ input: z.string() }).shape
  }]
}));

server.setRequestHandler("tools/call", async (request) => {
  if (request.params.name === "example_tool") {
    const { input } = request.params.arguments;
    return { content: [{ type: "text", text: `Result: ${input}` }] };
  }
  throw new Error("Unknown tool");
});

const transport = new {transport}();
await server.connect(transport);
'''

PY_SERVER_TEMPLATE = '''from mcp.server.fastmcp import FastMCP

mcp = FastMCP("{name}")

@mcp.tool()
async def example_tool(input: str) -> str:
    return f"Result: {input}"

@mcp.resource("example://{param}")
async def example_resource(param: str) -> str:
    return f"Resource data for {param}"

if __name__ == "__main__":
    mcp.run()
'''

def _op_create_server(kwargs: dict) -> dict:
    name = kwargs.get("server_name", "my-mcp-server")
    language = kwargs.get("language", "typescript")
    transport = kwargs.get("transport", "streamable-http")
    
    if language == "typescript":
        code = TS_SERVER_TEMPLATE.format(name=name, transport="StdioServerTransport" if transport == "stdio" else "StreamableHTTPServerTransport")
        return _op_result("MCP", f"Generated TypeScript MCP server: {name}", True, "create_server",
                        {"language": "typescript", "transport": transport, "code": code},
                        f"TypeScript MCP server '{name}' with {transport} transport. Use @modelcontextprotocol/sdk (v2).")
    else:
        code = PY_SERVER_TEMPLATE.format(name=name)
        return _op_result("MCP", f"Generated Python MCP server: {name}", True, "create_server",
                        {"language": "python", "code": code},
                        f"Python MCP server '{name}' using FastMCP. Install: pip install mcp")

def _op_validate_server(kwargs: dict) -> dict:
    name = kwargs.get("server_name", "my-mcp-server")
    guide = '''# Validate MCP Server
1. Check tools/list returns valid schemas
2. Test tools/call with sample inputs
3. Verify resources/list and resources/read
4. Run self-check script:
python -c "
from mcp.client.stdio import stdio_client
from mcp import ClientSession
async with stdio_client(['python', 'server.py']) as (r,w):
    async with ClientSession(r,w) as c:
        tools = await c.list_tools()
        print('Tools:', [t.name for t in tools.tools])
"'''
    return _op_result("MCP", f"Validation guide for {name}", True, "validate_server",
                    {"guide": guide}, f"Follow these steps to validate your MCP server '{name}'.")

def _op_create_evaluation(kwargs: dict) -> dict:
    name = kwargs.get("server_name", "my-mcp-server")
    guide = '''# Create Evaluation for MCP Server
Create XML with 10 complex QA pairs:
<evaluation>
  <qa_pair>
    <question>Complex question requiring multiple tool calls</question>
    <answer>Expected answer</answer>
  </qa_pair>
</evaluation>

Requirements: independent, read-only, complex, realistic, verifiable, stable.'''
    return _op_result("MCP", f"Evaluation guide for {name}", True, "create_evaluation",
                    {"guide": guide}, f"Create evaluation cases for your MCP server '{name}'.")

_OPERATIONS = {
    "create_server": _op_create_server,
    "add_tool": _op_add_tool,
    "add_resource": lambda k: _op_result("MCP", "Use add_tool pattern for resources", False, "add_resource"),
    "add_prompt": lambda k: _op_result("MCP", "Use add_tool pattern for prompts", False, "add_prompt"),
    "generate_typescript": _op_generate_typescript,
    "generate_python": _op_generate_python,
    "validate_server": _op_validate_server,
    "create_evaluation": _op_create_evaluation,
}

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "MCP",
            "summary": f"Unknown operation '{operation}'. Available: {', '.join(sorted(_OPERATIONS))}",
            "spoken_narrative": f"Unknown MCP operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        return handler(kwargs)
    except Exception as exc:
        return {
            "title": "MCP",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"MCP error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }

def _op_add_tool(kwargs: dict) -> dict:
    tool_name = kwargs.get("tool_name")
    tool_desc = kwargs.get("tool_description")
    tool_schema = kwargs.get("tool_schema", {})
    language = kwargs.get("language", "typescript")
    
    if not tool_name or not tool_desc:
        return _op_result("MCP", "tool_name and tool_description required", False, "add_tool")
    
    if language == "typescript":
        code = f'''server.setRequestHandler("tools/list", async () => ({{
  tools: [{{
    name: "{tool_name}",
    description: "{tool_desc}",
    inputSchema: z.object({{ {', '.join(f'{k}: z.{v}()' for k, v in tool_schema.items())} }}).shape
  }}]
}}));

server.setRequestHandler("tools/call", async (request) => {{
  if (request.params.name === "{tool_name}") {{
    const args = request.params.arguments;
    return {{ content: [{{ type: "text", text: `Tool executed with ${{JSON.stringify(args)}}` }}] }};
  }}
}});'''
    else:
        props = ', '.join(f'{k}: {v}' for k, v in tool_schema.items())
        code = f'''@mcp.tool()
async def {tool_name}({props}) -> str:
    """{tool_desc}"""
    return f"Tool executed with {{locals()}}"'''
    
    return _op_result("MCP", f"Generated {language} tool: {tool_name}", True, "add_tool",
                    {"language": language, "tool_name": tool_name, "code": code},
                    f"Add this to your {language} MCP server to register the '{tool_name}' tool.")

def _op_generate_typescript(kwargs: dict) -> dict:
    name = kwargs.get("server_name", "my-mcp-server")
    transport = kwargs.get("transport", "streamable-http")
    code = TS_SERVER_TEMPLATE.format(name=name, transport="StdioServerTransport" if transport == "stdio" else "StreamableHTTPServerTransport")
    return _op_result("MCP", f"TypeScript MCP server template: {name}", True, "generate_typescript",
                    {"language": "typescript", "transport": transport, "code": code},
                    f"Complete TypeScript MCP server using @modelcontextprotocol/sdk (v2). Run: npm install @modelcontextprotocol/sdk zod")

def _op_generate_python(kwargs: dict) -> dict:
    name = kwargs.get("server_name", "my-mcp-server")
    code = PY_SERVER_TEMPLATE.format(name=name)
    return _op_result("MCP", f"Python MCP server template: {name}", True, "generate_python",
                    {"language": "python", "code": code},
                    f"Complete Python MCP server using FastMCP. Install: pip install mcp")

def _resolve_path(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p