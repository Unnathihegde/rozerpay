import { create } from "zustand";

import type { CatalogProduct, Order, Quote } from "./api";

export type NodeId = "ai" | "policy" | "execution" | "razorpay" | "ledger";
export type PipelineStage = "idle" | NodeId;
export type NodeStatus = "idle" | "active" | "done" | "blocked" | "failed";

export type Toast = {
  id: string;
  title: string;
  detail: string;
  tone: "success" | "warning" | "error";
};

type DashboardState = {
  selectedProduct: CatalogProduct | null;
  activeQuote: Quote | null;
  activeOrder: Order | null;
  pipelineStage: PipelineStage;
  pipelineNodeStatus: Record<NodeId, NodeStatus>;
  toasts: Toast[];
  setSelectedProduct: (product: CatalogProduct | null) => void;
  setActiveQuote: (quote: Quote | null) => void;
  setActiveOrder: (order: Order | null) => void;
  setPipelineStage: (stage: PipelineStage) => void;
  setNodeStatus: (node: NodeId, status: NodeStatus) => void;
  addToast: (toast: Toast) => void;
  removeToast: (id: string) => void;
  resetTransaction: () => void;
};

const idleNodes: Record<NodeId, NodeStatus> = {
  ai: "idle",
  policy: "idle",
  execution: "idle",
  razorpay: "idle",
  ledger: "idle"
};

export const useDashboardStore = create<DashboardState>((set) => ({
  selectedProduct: null,
  activeQuote: null,
  activeOrder: null,
  pipelineStage: "idle",
  pipelineNodeStatus: idleNodes,
  toasts: [],
  setSelectedProduct: (selectedProduct) => set({ selectedProduct }),
  setActiveQuote: (activeQuote) => set({ activeQuote }),
  setActiveOrder: (activeOrder) => set({ activeOrder }),
  setPipelineStage: (pipelineStage) => set({ pipelineStage }),
  setNodeStatus: (node, status) => set((state) => ({ pipelineNodeStatus: { ...state.pipelineNodeStatus, [node]: status } })),
  addToast: (toast) => set((state) => ({ toasts: [...state.toasts, toast] })),
  removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) })),
  resetTransaction: () => set({ selectedProduct: null, activeQuote: null, activeOrder: null, pipelineStage: "idle", pipelineNodeStatus: idleNodes })
}));
