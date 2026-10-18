import React, { useMemo } from "react";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { GraphEdgeDTO, GraphNodeDTO, MemoryTier } from "../api/types";
import { AgentHiveGraphNode } from "./CustomNodes";

interface MemoryGraphCanvasProps {
  nodes: GraphNodeDTO[];
  edges: GraphEdgeDTO[];
  selectedTier: MemoryTier | "ALL";
  searchQuery: string;
  onSelectNode: (node: GraphNodeDTO) => void;
}

const nodeTypes = {
  agenthiveNode: AgentHiveGraphNode,
};

const TIER_Y_OFFSET: Record<MemoryTier, number> = {
  COORDINATION: 40,
  EPISODIC: 210,
  SEMANTIC: 390,
  PROCEDURAL: 560,
};

export const MemoryGraphCanvas: React.FC<MemoryGraphCanvasProps> = ({
  nodes,
  edges,
  selectedTier,
  searchQuery,
  onSelectNode,
}) => {
  const { flowNodes, flowEdges } = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const filteredNodes = nodes.filter((n) => {
      if (selectedTier !== "ALL" && n.tier !== selectedTier) return false;
      if (q && !n.label.toLowerCase().includes(q) && !n.node_type.toLowerCase().includes(q)) {
        return false;
      }
      return true;
    });

    const visibleIds = new Set(filteredNodes.map((n) => n.id));
    const tierCounters: Record<string, number> = {
      COORDINATION: 0,
      EPISODIC: 0,
      SEMANTIC: 0,
      PROCEDURAL: 0,
    };

    const rfNodes: Node[] = filteredNodes.map((n) => {
      const idx = tierCounters[n.tier] ?? 0;
      tierCounters[n.tier] = idx + 1;
      const col = idx % 6;
      const rowOffset = Math.floor(idx / 6) * 90;

      return {
        id: n.id,
        type: "agenthiveNode",
        position: {
          x: 50 + col * 245,
          y: (TIER_Y_OFFSET[n.tier] ?? 200) + rowOffset,
        },
        data: {
          label: n.label,
          nodeType: n.node_type,
          tier: n.tier,
          status: n.status,
          isGlowing: n.is_glowing,
          raw: n,
        },
      };
    });

    const rfEdges: Edge[] = edges
      .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
      .map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: e.is_active_path,
        style: {
          stroke: e.is_active_path ? "#22d3ee" : "#475569",
          strokeWidth: e.is_active_path ? 2.5 : 1.3,
        },
        labelStyle: {
          fill: e.is_active_path ? "#67e8f9" : "#94a3b8",
          fontSize: 10,
          fontFamily: "monospace",
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: e.is_active_path ? "#22d3ee" : "#475569",
        },
      }));

    return { flowNodes: rfNodes, flowEdges: rfEdges };
  }, [nodes, edges, selectedTier, searchQuery]);

  if (flowNodes.length === 0) {
    return (
      <div className="h-[540px] rounded-xl bg-[#0b1021] border border-slate-800 flex flex-col items-center justify-center p-6 text-center">
        <p className="text-sm font-semibold text-slate-300">
          No graph nodes in this tenant view yet.
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Click &ldquo;Seed 120-Episode Demo Corpus&rdquo; above or record a new Episode to populate FalkorDB.
        </p>
      </div>
    );
  }

  return (
    <div className="h-[560px] w-full rounded-xl overflow-hidden border border-slate-800 bg-[#060913]">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        fitView
        onNodeClick={(_evt, node) => {
          const raw = (node.data as Record<string, unknown>)?.raw as GraphNodeDTO | undefined;
          if (raw) {
            onSelectNode(raw);
          }
        }}
      >
        <Background color="#1e293b" gap={22} />
        <Controls />
      </ReactFlow>
    </div>
  );
};