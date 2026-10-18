import json
import os
import sys
import uuid
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from app.domain.tenant import TenantCreateRequest
from app.services.tenant_service import get_tenant_service

_API_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.asyncio
async def test_c02_external_mcp_client_write_and_retrieve_end_to_end() -> None:
    """
    Verifies Constraint C-02: An external MCP client connects to app.mcp_server over stdio,
    discovers tools, writes a new episode via remember_episode, and retrieves it via assemble_context.
    """
    tenant_id = f"mcp-tenant-{uuid.uuid4().hex[:6]}"
    get_tenant_service().provision_tenant(
        TenantCreateRequest(
            tenant_id=tenant_id,
            display_name=f"MCP Integration Tenant {tenant_id}",
            description="End-to-end MCP stdio verification tenant",
            is_demo=True,
        )
    )

    env = dict(os.environ)
    env["PYTHONPATH"] = str(_API_ROOT)
    env["AGENTHIVE_MCP_TENANT_ID"] = tenant_id

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
        env=env,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # 1. Verify MCP tools are advertised
            tools_result = await session.list_tools()
            tool_names = {t.name for t in tools_result.tools}
            assert "remember_episode" in tool_names
            assert "assemble_context" in tool_names
            assert "search_memory" in tool_names
            assert "get_session_history" in tool_names
            assert "create_handoff" in tool_names

            # 2. Write an episode via MCP tool call
            write_res = await session.call_tool(
                "remember_episode",
                arguments={
                    "content": (
                        "MCP Client verified FalkorDB persistence. "
                        "FACT: PaymentGateway max_connections = 1024. "
                        "PROCEDURE: Scale PaymentGateway Ingress | "
                        "TRIGGER: When PaymentGateway max_connections approaches 1024 | "
                        "STEPS: 1. Add ingress replica; 2. Rebalance connection pool"
                    ),
                    "agent_id": "mcp-copilot-agent",
                    "session_id": "sess-mcp-e2e",
                    "importance_score": 0.92,
                },
            )
            assert not write_res.isError
            write_content = write_res.content[0]
            assert isinstance(write_content, TextContent)
            ep_data = json.loads(write_content.text)
            assert ep_data["tenant_id"] == tenant_id
            assert ep_data["extraction_status"] == "COMPLETED"

            # 3. Retrieve unified context via MCP tool call
            ctx_res = await session.call_tool(
                "assemble_context",
                arguments={
                    "query": "PaymentGateway max_connections ingress scaling",
                    "agent_id": "mcp-copilot-agent",
                },
            )
            assert not ctx_res.isError
            context_content = ctx_res.content[0]
            assert isinstance(context_content, TextContent)
            ctx_pkg = json.loads(context_content.text)
            assert ctx_pkg["tenant_id"] == tenant_id
            assert len(ctx_pkg["episodes"]) == 1
            assert ctx_pkg["episodes"][0]["episode"]["id"] == ep_data["id"]
            assert any(f["object_value"] == "1024" for f in ctx_pkg["facts"])
            assert len(ctx_pkg["procedures"]) == 1