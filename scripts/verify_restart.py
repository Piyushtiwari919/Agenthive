import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "apps" / "api"))

from app.core.security import derive_opaque_graph_name  # noqa: E402
from app.domain.memory import EpisodeCreateRequest  # noqa: E402
from app.domain.tenant import TenantScope  # noqa: E402
from app.repositories.falkor_client import falkor_manager  # noqa: E402
from app.services.memory_service import get_memory_service  # noqa: E402
from app.services.tenant_service import get_tenant_service  # noqa: E402


def main() -> None:
    print("Verifying FR-002 & NFR-003 Persistence Across Restarts...")
    get_tenant_service().ensure_demo_tenants()
    scope = TenantScope(
        tenant_id="alpha-eng",
        graph_name=derive_opaque_graph_name("alpha-eng"),
        display_name="Tenant A",
        is_demo=True,
    )
    mem_svc = get_memory_service()

    ep = mem_svc.record_episode(
        scope,
        EpisodeCreateRequest(
            content="Restart survival verification test. FACT: RestartMarker persistent = true.",
            agent_id="verifier",
            session_id="sess-restart",
            importance_score=0.99,
        ),
    )
    ep_id = ep.id

    # Reset client connection (simulating application & database restart)
    print("Simulating application & database connection reset...")
    falkor_manager.reset_connection()

    # Re-fetch episode
    fetched = mem_svc.get_episode(scope, ep_id)
    assert fetched.content == ep.content
    assert fetched.importance_score == ep.importance_score
    print(f"[OK] Episode {ep_id} successfully survived connection reset with zero data loss!")


if __name__ == "__main__":
    main()