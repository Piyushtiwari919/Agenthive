import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiClient } from "../api/client";
import type { TenantInfo } from "../api/types";

interface TenantContextValue {
  tenantId: string;
  tenants: TenantInfo[];
  activeTenantInfo: TenantInfo | undefined;
  switchTenant: (newTenantId: string) => void;
  refreshTenants: () => Promise<void>;
  provisionNewTenant: (payload: {
    tenant_id: string;
    display_name: string;
    description?: string;
  }) => Promise<TenantInfo>;
  scopeEpoch: number;
}

const TenantContext = createContext<TenantContextValue | undefined>(undefined);

const DEFAULT_FALLBACK_TENANTS: TenantInfo[] = [
  {
    tenant_id: "alpha-eng",
    display_name: "Tenant A — Alpha Core Engineering",
    description: "Platform & Payments Engineering Team",
    graph_name: "ah_tenant_alpha",
    is_demo: true,
    created_at: new Date().toISOString(),
  },
  {
    tenant_id: "beta-sec",
    display_name: "Tenant B — Beta Cloud Security",
    description: "Zero-Trust Security Operations Team",
    graph_name: "ah_tenant_beta",
    is_demo: true,
    created_at: new Date().toISOString(),
  },
];

export const TenantProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [tenantId, setTenantId] = useState<string>("alpha-eng");
  const [tenants, setTenants] = useState<TenantInfo[]>(DEFAULT_FALLBACK_TENANTS);
  const [scopeEpoch, setScopeEpoch] = useState<number>(1);

  const refreshTenants = useCallback(async () => {
    try {
      const list = await apiClient.listTenants();
      if (list.length > 0) {
        setTenants(list);
      }
    } catch {
      // Keep default fallback list if backend is warming up
    }
  }, []);

  useEffect(() => {
    void refreshTenants();
  }, [refreshTenants]);

  const switchTenant = useCallback((newTenantId: string) => {
    setTenantId(newTenantId);
    // Incrementing scopeEpoch forces all tenant-scoped views to discard prior tenant state immediately (FR-016)
    setScopeEpoch((prev) => prev + 1);
  }, []);

  const provisionNewTenant = useCallback(
    async (payload: { tenant_id: string; display_name: string; description?: string }) => {
      const created = await apiClient.createTenant({ ...payload, is_demo: false });
      await refreshTenants();
      switchTenant(created.tenant_id);
      return created;
    },
    [refreshTenants, switchTenant]
  );

  const activeTenantInfo = tenants.find((t) => t.tenant_id === tenantId);

  return (
    <TenantContext.Provider
      value={{
        tenantId,
        tenants,
        activeTenantInfo,
        switchTenant,
        refreshTenants,
        provisionNewTenant,
        scopeEpoch,
      }}
    >
      {children}
    </TenantContext.Provider>
  );
};

export function useTenantScope(): TenantContextValue {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error("useTenantScope must be used within a TenantProvider");
  }
  return context;
}