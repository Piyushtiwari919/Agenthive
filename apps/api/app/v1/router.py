from fastapi import APIRouter

from app.v1 import (
    agents,
    context,
    diagnostics,
    episodes,
    graph,
    handoffs,
    health,
    procedures,
    semantic,
    stream,
    tasks,
    tenants,
)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health.router)
v1_router.include_router(tenants.router)
v1_router.include_router(episodes.router)
v1_router.include_router(semantic.router)
v1_router.include_router(procedures.router)
v1_router.include_router(context.router)
v1_router.include_router(agents.router)
v1_router.include_router(handoffs.router)
v1_router.include_router(tasks.router)
v1_router.include_router(graph.router)
v1_router.include_router(stream.router)
v1_router.include_router(diagnostics.router)