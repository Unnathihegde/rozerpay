import axios from "axios";

export type Product = {
  id: string;
  name: string;
  category: string;
  price_paise: number;
  stock_qty: number;
};

export type CatalogProduct = {
  "@type": "Product";
  "@id": string;
  name: string;
  category: string;
  offers: {
    "@type": "Offer";
    priceCurrency: "INR";
    price: string;
    availability: string;
  };
};

export type Catalog = {
  "@context": "https://schema.org";
  "@type": "ItemList";
  itemListElement: CatalogProduct[];
};

export type Quote = {
  quote_id: string;
  product_id: string;
  quantity: number;
  locked_price_paise: number;
  currency: "INR";
  expires_at: string;
  signature: string;
};

export type Upsell = {
  suggested_item: string;
  reason: string;
  margin_delta: string;
} | null;

export type Order = {
  order_id: string;
  amount_paise: number;
  currency: "INR";
  settlement_methods: string[];
  razorpay_order_id?: string;
  payment_link_url?: string;
  status?: string;
};

export type Approval = { approval_id: string; status?: string };

export type PendingApproval = {
  approval_id: string;
  order_id: string;
  amount_paise: number;
  status: "pending";
  created_at: string;
};

export type PendingApprovals = { items: PendingApproval[]; count: number };

export type AuditEntry = {
  step: string;
  timestamp: string;
  details: Record<string, unknown>;
};

export type Audit = { order_id: string; items: AuditEntry[]; count: number };

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  headers: { "Content-Type": "application/json" }
});

export const getCatalog = async (): Promise<Catalog> => (await client.get<Catalog>("/catalog.jsonld")).data;
export const createQuote = async (product_id: string, quantity: number): Promise<Quote> =>
  (await client.post<Quote>("/v1/quote", { product_id, quantity })).data;
export const getUpsell = async (quote_id: string): Promise<Upsell> =>
  (await client.post<Upsell>(`/v1/quote/${quote_id}/upsell`)).data;
export const initiateCheckout = async (quote_id: string, nonce: string): Promise<Order> =>
  (await client.post<Order>("/v1/checkout", { quote_id, nonce }, { validateStatus: (status) => status === 402 })).data;
export const payOrder = async (order_id: string): Promise<Order | Approval> =>
  (await client.post<Order | Approval>(`/v1/orders/${order_id}/pay`, { mode: "link" })).data;
export const getAudit = async (order_id: string): Promise<Audit> =>
  (await client.get<Audit>(`/v1/orders/${order_id}/audit`)).data;
export const getPendingApprovals = async (): Promise<PendingApprovals> =>
  (await client.get<PendingApprovals>("/v1/approvals")).data;
export const approveRequest = async (approval_id: string): Promise<Approval> =>
  (await client.post<Approval>(`/v1/approvals/${approval_id}/approve`)).data;
export const rejectRequest = async (approval_id: string): Promise<Approval> =>
  (await client.post<Approval>(`/v1/approvals/${approval_id}/reject`)).data;
