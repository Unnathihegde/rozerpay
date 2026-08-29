import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Bell, Bot, Check, ChevronDown, CircleDollarSign, Clock3, CreditCard, FileText, Heart, Hexagon, KeyRound, LockKeyhole, Menu, Search, ShieldCheck, ShoppingBag, Sparkles, Star, X, Zap } from "lucide-react";
import { approveRequest, createQuote, getCatalog, getLedger, getOrder, getPendingApprovals, getUpsell, initiateCheckout, payOrder, rejectRequest, type LedgerItem, type Order, type Quote, type Upsell, type PendingApproval } from "./api";
import AddProduct from "./AddProduct";

type Product = { id: string; name: string; category: string; price: number; image: string | null; description: string; delivery: string; compatibility: string; rating: string; availability: "In stock" | "Out of stock" | "Unknown" };
type CartItem = { product: Product; quantity: number; quote?: Quote };

const money = (paise: number) => `₹${(paise / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

function normalizeCatalog(catalog: Awaited<ReturnType<typeof getCatalog>>): Product[] {
  return catalog.itemListElement.map((item, index) => ({ id: item["@id"], name: item.name, category: item.category, price: Math.round(Number(item.offers.price) * 100), image: null, description: "Thoughtfully selected for your everyday setup.", delivery: index % 2 ? "2–3 days" : "Tomorrow", compatibility: "Works beautifully together", rating: "4.8", availability: item.offers.availability.includes("OutOfStock") ? "Out of stock" : item.offers.availability.includes("InStock") ? "In stock" : "Unknown" }));
}

function LegacyGatewayDashboard({ onBack }: { onBack: () => void }) {
  const stages = [
    { name: "AI Intent", icon: Sparkles, state: "done" },
    { name: "Policy Check", icon: ShieldCheck, state: "done" },
    { name: "Execution", icon: Zap, state: "active" },
    { name: "Razorpay", icon: CreditCard, state: "idle" },
    { name: "Ledger", icon: FileText, state: "idle" },
  ];
  const [approvalOpen, setApprovalOpen] = useState(false);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const loadApprovals = async () => {
    setApprovalLoading(true);
    setApprovalError(null);
    try {
      const result = await getPendingApprovals();
      setApprovals(result.items);
    } catch {
      setApprovalError("Unable to load pending approvals.");
    } finally {
      setApprovalLoading(false);
    }
  };
  const products = [
    ["Frame USB-C Camera Hub", "Camera", "₹1,899.00", "12 in stock", "Tomorrow"],
    ["ClearView Lens Care Kit", "Accessory", "₹799.00", "34 in stock", "2–3 days"],
    ["Luma Mini Studio Light", "Camera", "₹3,499.00", "8 in stock", "Friday"],
    ["Nomad Camera Strap", "Accessory", "₹1,299.00", "21 in stock", "Tomorrow"],
  ];
  const ledger = [
    ["14:32:08.421", "execution_started", "{ order: 'ord_7f2a', amount: 199900 }", "success"],
    ["14:32:08.194", "policy_check_passed", "{ limit: 1000000, risk: 'low' }", "success"],
    ["14:32:07.982", "quote_generated", "{ quote: 'qt_91c2', ttl: 900 }", "pending"],
    ["14:32:07.614", "intent_received", "{ product: 'camera-hub', qty: 1 }", "success"],
    ["14:31:55.203", "approval_requested", "{ amount: 6500000, reason: 'limit' }", "pending"],
    ["14:31:49.877", "payment_failed", "{ order: 'ord_7e91', recovery: true }", "failed"],
  ];
  return <div className="gateway-shell">
    <header className="gateway-topbar"><button className="gateway-brand" onClick={onBack}><span className="gateway-mark"><Hexagon /></span><span><b>MERCHANT AGENT GATEWAY</b><small>TRANSACTION CONTROL PLANE</small></span></button><div className="gateway-top-actions"><span className="mode-pill">TEST MODE</span><span className="connection-dot"><i /> LIVE</span><button className="bell-button" onClick={() => { setApprovalOpen(true); void loadApprovals(); }} aria-label="Open approval queue"><Bell /><b>{approvals.length}</b></button></div><AddProduct /> </header>
    <div className="gateway-layout"><section className="inventory-panel gateway-panel"><div className="gateway-panel-head"><div><span className="gateway-eyebrow">CATALOG / LIVE INVENTORY</span><h2>Product surface</h2></div><CircleDollarSign /></div><div className="inventory-filters"><button className="selected">All</button><button>Camera</button><button>Audio</button><button>Accessory</button></div><div className="inventory-grid">{products.map(([name, cat, price, stock, delivery], i) => <article className="inventory-card" key={name}><div className={`inventory-image image-${i}`}><span>{cat.slice(0, 1)}</span></div><div><span className="category-label">{cat}</span><h3>{name}</h3><strong>{price}</strong><p><i className="stock-dot" />{stock} <em>· {delivery}</em></p></div></article>)}</div><div className="price-control"><span>PRICE RANGE</span><div><i /><i /></div><b>₹0 — ₹10,000</b></div></section>
      <section className="gateway-right"><div className="pipeline-panel gateway-panel"><div className="gateway-panel-head"><div><span className="gateway-eyebrow">PIPELINE / DECISION TRACE</span><h2>Transaction in motion</h2></div><span className="trace-id">TRACE_7F2A</span></div><div className="pipeline">{stages.map(({ name, icon: Icon, state }, i) => <div className="stage-wrap" key={name}><div className={`stage-node ${state}`}>{state === "done" ? <Check /> : <Icon />}</div><span>{name}</span>{i < stages.length - 1 && <div className={`stage-line ${i < 2 ? "passed" : ""}`}><i /></div>}</div>)}</div><div className="pipeline-status"><span className="pulse-dot" /><div><b>Execution active</b><span>Creating a secure payment order for the locked quote.</span></div><span className="status-time">+00:00:02.4</span></div></div><div className="context-panel gateway-panel"><div className="gateway-panel-head"><div><span className="gateway-eyebrow">TRANSACTION CONTEXT</span><h2>Frame USB-C Camera Hub</h2></div><LockKeyhole /></div><div className="context-main"><div className="countdown-ring"><strong>14:42</strong><span>PRICE LOCK</span></div><div><span className="gateway-eyebrow">LOCKED PRICE</span><b className="locked-price">₹1,899.00</b><p className="signature"><KeyRound /> sig_8b2e…f91a <button aria-label="Copy signature">□</button></p></div></div><div className="gateway-upsell"><Sparkles /><div><b>Suggested add-on</b><span>Lens Cleaner Kit <em>· +12% margin</em></span></div><button>Accept</button><button className="skip">Skip</button></div></div></section></div>
    <section className="ledger-panel gateway-panel"><div className="gateway-panel-head"><div><span className="gateway-eyebrow">LIVE AUDIT LEDGER</span><h2>Recent activity</h2></div><span className="ledger-live"><i /> STREAMING</span></div><div className="ledger-list">{ledger.map(([time, step, detail, state]) => <div className={`ledger-row ${state}`} key={time + step}><time>{time}</time><code>{step}</code><span>{detail}</span><b>{state === "success" ? "PASS" : state === "pending" ? "WAIT" : "FAIL"}</b></div>)}</div></section>
    <div className="gateway-foot"><button onClick={onBack}>← Return to storefront</button><span><ShieldCheck /> AI Commerce Gateway protected</span><span className="mono">v0.8.4 · us-east-1</span></div>
    {approvalOpen && <div className="approval-overlay" onClick={() => setApprovalOpen(false)}><aside className="approval-drawer" onClick={(e) => e.stopPropagation()}><div className="approval-head"><div><span className="gateway-eyebrow">HUMAN REVIEW</span><h2>Approval Queue</h2></div><button onClick={() => setApprovalOpen(false)} aria-label="Close approval queue"><X /></button></div>{approvalLoading ? <div className="approval-item"><span className="approval-flag"><Clock3 /></span><div><b>Loading pending approvals...</b><small>Checking the backend approval queue.</small></div></div> : approvalError ? <div className="approval-item"><span className="approval-flag"><X /></span><div><b>{approvalError}</b><button className="text-button" onClick={() => void loadApprovals()}>Retry</button></div></div> : approvals.length === 0 ? <div className="approval-item"><span className="approval-flag"><Check /></span><div><b>No pending approvals</b><small>The queue is clear.</small></div></div> : approvals.map((approval) => <div key={approval.approval_id}><div className="approval-item"><span className="approval-flag"><LockKeyhole /></span><div><b>Order {approval.order_id}</b><p>{`₹${(approval.amount_paise / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}</p><small>Requested {approval.created_at}</small></div></div><div className="approval-actions"><button className="approve" onClick={async () => { await approveRequest(approval.approval_id); await loadApprovals(); }}>Approve</button><button className="reject" onClick={async () => { await rejectRequest(approval.approval_id); await loadApprovals(); }}>Reject</button></div></div>)}</aside></div>}
  </div>;
}

function GatewayDashboard({ onBack, products, connection }: { onBack: () => void; products: Product[]; connection: string }) {
  const [approvalOpen, setApprovalOpen] = useState(false);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [ledger, setLedger] = useState<LedgerItem[]>([]);
  const [ledgerLoading, setLedgerLoading] = useState(true);
  const [ledgerError, setLedgerError] = useState<string | null>(null);
  const loadApprovals = async () => {
    setApprovalLoading(true);
    setApprovalError(null);
    try {
      const result = await getPendingApprovals();
      setApprovals(result.items);
    } catch {
      setApprovalError("Unable to load pending approvals.");
    } finally {
      setApprovalLoading(false);
    }
  };
  useEffect(() => {
    getLedger().then((result) => {
      setLedger(result.items);
      setLedgerError(null);
    }).catch(() => {
      setLedgerError("Unable to load activity.");
    }).finally(() => setLedgerLoading(false));
  }, []);
  const statusLabel = connection === "live" ? "Connected" : connection === "demo" ? "Catalog unavailable" : "Connecting";
  return <div className="ops-shell">
    <header className="ops-header"><button className="ops-brand" onClick={onBack}><span className="ops-brand-mark"><Hexagon /></span><span><strong>Merchant Gateway</strong><small>Operations console</small></span></button><nav className="ops-nav" aria-label="Gateway sections"><a className="active" href="#ops-catalog">Catalog</a><a href="#ops-activity">Activity</a></nav><div className="ops-header-actions"><span className={`ops-status ${connection}`}><i /> {statusLabel}</span><span className="ops-mode">Test mode</span><button className="ops-icon-button" onClick={() => { setApprovalOpen(true); void loadApprovals(); }} aria-label="Open approval queue"><Bell /><b>{approvals.length}</b></button><AddProduct /></div></header>
    <main className="ops-main"><section className="ops-intro"><div><p className="ops-kicker">Merchant operations</p><h1>Gateway control</h1><p>Manage the products your agents can discover and review payment exceptions as they happen.</p></div><div className="ops-intro-status"><span className="ops-status-dot" /> Gateway online <small>API connected</small></div></section>
      <section className="ops-section" id="ops-catalog"><div className="ops-section-heading"><div><p className="ops-kicker">Catalog</p><h2>Products</h2></div><span>{products.length} {products.length === 1 ? "product" : "products"}</span></div>{products.length === 0 ? <div className="ops-empty"><ShoppingBag /><div><strong>No products yet</strong><p>Your live catalog is empty. Add a product to make it available to buyer agents.</p></div></div> : <div className="ops-table-wrap"><table className="ops-table"><thead><tr><th>Product</th><th>Category</th><th>Price</th><th>Availability</th><th><span className="sr-only">Action</span></th></tr></thead><tbody>{products.map((product) => <tr key={product.id}><td><div className="ops-product"><span className="ops-product-placeholder">{product.name.slice(0, 1).toUpperCase()}</span><span><strong>{product.name}</strong><small>{product.id}</small></span></div></td><td>{product.category}</td><td className="ops-number">{money(product.price)}</td><td><span className={`ops-availability ${product.availability.toLowerCase().replace(" ", "-")}`}><i />{product.availability}</span></td><td><button className="ops-row-action" onClick={() => onBack()}>View in store <ArrowRight /></button></td></tr>)}</tbody></table></div>}</section>
      <section className="ops-section ops-activity" id="ops-activity"><div className="ops-section-heading"><div><p className="ops-kicker">Audit stream</p><h2>Recent activity</h2></div><button className="ops-refresh" onClick={() => { setLedgerLoading(true); void getLedger().then((result) => { setLedger(result.items); setLedgerError(null); }).catch(() => setLedgerError("Unable to load activity.")).finally(() => setLedgerLoading(false)); }}>Refresh</button></div>{ledgerLoading ? <div className="ops-empty ops-empty-compact"><Clock3 /><div><strong>Loading activity</strong><p>Checking the gateway ledger.</p></div></div> : ledgerError ? <div className="ops-empty ops-empty-compact"><X /><div><strong>{ledgerError}</strong><p>Try refreshing the activity stream.</p></div></div> : ledger.length === 0 ? <div className="ops-empty ops-empty-compact"><FileText /><div><strong>No activity to review</strong><p>Payment and ledger events will be shown here when an agent starts a transaction.</p></div></div> : <div className="ops-activity-list">{ledger.map((entry) => <div className="ops-activity-row" key={entry.id}><span className="ops-activity-dot" /><time>{entry.timestamp}</time><strong>{entry.step}</strong><span>{entry.order_id ?? "System event"}</span></div>)}</div>}</section>
    </main>
    <footer className="ops-footer"><button onClick={onBack}>← Storefront</button><span>Merchant Gateway <b>v0.8.4</b></span><span>Protected operations</span></footer>
    {approvalOpen && <div className="ops-overlay" onClick={() => setApprovalOpen(false)}><aside className="ops-drawer" onClick={(event) => event.stopPropagation()}><div className="ops-drawer-head"><div><p className="ops-kicker">Human review</p><h2>Approval queue</h2></div><button className="ops-close" onClick={() => setApprovalOpen(false)} aria-label="Close approval queue"><X /></button></div>{approvalLoading ? <div className="ops-drawer-state"><Clock3 /><p>Loading pending approvals...</p></div> : approvalError ? <div className="ops-drawer-state"><X /><p>{approvalError}</p><button className="ops-text-button" onClick={() => void loadApprovals()}>Retry</button></div> : approvals.length === 0 ? <div className="ops-drawer-state"><Check /><p>No pending approvals</p><small>The queue is clear.</small></div> : approvals.map((approval) => <div className="ops-approval" key={approval.approval_id}><div><strong>Order {approval.order_id}</strong><span>{money(approval.amount_paise)}</span><small>{approval.created_at}</small></div><div><button className="ops-approve" onClick={async () => { await approveRequest(approval.approval_id); await loadApprovals(); }}>Approve</button><button className="ops-reject" onClick={async () => { await rejectRequest(approval.approval_id); await loadApprovals(); }}>Reject</button></div></div>)}</aside></div>}
  </div>;
}

export default function App() {
  const reduceMotion = useReducedMotion();
  const [products, setProducts] = useState<Product[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [connection, setConnection] = useState("connecting");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const [selected, setSelected] = useState<Product | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [upsell, setUpsell] = useState<Upsell>(null);
  const [quoteBusy, setQuoteBusy] = useState(false);
  const [assistant, setAssistant] = useState(false);
  const [assistantText, setAssistantText] = useState("");
  const [checkout, setCheckout] = useState(false);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [order, setOrder] = useState<Order | null>(null);
  const [payment, setPayment] = useState<"idle" | "pending" | "approval" | "ready" | "failed">("idle");
  const [showTrust, setShowTrust] = useState(false);
  const [view, setView] = useState<"store" | "gateway">("store");

  useEffect(() => { getCatalog().then((data) => { setProducts(normalizeCatalog(data)); setConnection("live"); setCatalogError(null); }).catch(() => { setProducts([]); setConnection("error"); setCatalogError("The live catalog could not be loaded."); }).finally(() => setCatalogLoading(false)); }, []);
  const categories = ["All", ...Array.from(new Set(products.map((p) => p.category)))];
  const filtered = useMemo(() => products.filter((p) => (category === "All" || p.category === category) && p.name.toLowerCase().includes(query.toLowerCase())), [products, query, category]);
  const total = cart.reduce((sum, item) => sum + item.product.price * item.quantity, 0);
  const bestMatch = filtered[0] ?? products[0];

  const addToCart = (product: Product, quantity = 1) => setCart((items) => { const existing = items.find((item) => item.product.id === product.id); return existing ? items.map((item) => item.product.id === product.id ? { ...item, quantity: item.quantity + quantity } : item) : [...items, { product, quantity }]; });
  const requestQuote = async (product: Product) => { setQuoteBusy(true); setQuoteError(null); try { const result = await createQuote(product.id, 1); setQuote(result); setSelected(product); setUpsell(await getUpsell(result.quote_id)); } catch (error) { setQuoteError("The quote could not be created. Check stock and try again."); throw error; } finally { setQuoteBusy(false); } };
  const startCheckout = async () => { if (!quote) return; setCheckout(true); setCheckoutError(null); try { const result = await initiateCheckout(quote.quote_id, crypto.randomUUID()); setOrder(result); setPayment("pending"); } catch { setOrder(null); setCheckoutError("The order could not be created. Check the quote and try again."); } };
  const refreshOrderState = async (orderId = order?.order_id) => {
    if (!orderId) return null;
    try {
      const result = await getOrder(orderId);
      setOrder((current) => ({ ...(current ?? {}), ...result }));
      const status = (result.status ?? "").toLowerCase();
      if (status === "paid") setPayment("ready");
      else if (status === "failed" || status === "recovered_pending_retry") setPayment("failed");
      else if (status === "awaiting_payment") setPayment("pending");
      return result;
    } catch {
      return null;
    }
  };
  const createPayment = async () => { if (!order) return; setPayment("pending"); try { const result = await payOrder(order.order_id); if ("approval_id" in result) { setPayment("approval"); return; } const nextOrder = { ...order, ...result, payment_link_url: result.payment_link_url ?? result.razorpay_payment_link_url ?? order.payment_link_url, status: result.status ?? order.status }; setOrder(nextOrder); if (nextOrder.payment_link_url) window.open(nextOrder.payment_link_url, "_blank", "noopener,noreferrer"); setPayment("pending"); void refreshOrderState(order.order_id); } catch { setPayment("failed"); } };

  useEffect(() => {
    if (!checkout || !order?.order_id) return;
    const terminalStates = new Set(["paid", "failed", "recovered_pending_retry"]);
    const status = (order.status ?? "").toLowerCase();
    if (terminalStates.has(status)) return;

    let timeoutId: number | undefined;
    let active = true;

    const poll = async () => {
      const fresh = await refreshOrderState(order.order_id);
      if (!active || !fresh) return;
      const freshStatus = (fresh.status ?? "").toLowerCase();
      if (terminalStates.has(freshStatus)) return;
      timeoutId = window.setTimeout(poll, 3000);
    };

    void poll();
    return () => {
      active = false;
      if (timeoutId) window.clearTimeout(timeoutId);
    };
  }, [checkout, order?.order_id, order?.status]);

  if (view === "gateway") return <GatewayDashboard products={products} connection={connection} onBack={() => setView("store")} />;

  return <div className="site-shell">
    <header className="site-header"><a className="logo" href="#top"><span className="logo-dot" />nura</a><nav><a href="#shop">Shop</a><a href="#shop">Categories</a><a href="#protected">How it works</a></nav><button className="gateway-link" onClick={() => setView("gateway")}><Zap /> Gateway</button><div className="header-actions"><span className={`live-pill ${connection}`}><span /> {connection === "live" ? "Live catalog" : connection === "error" ? "Catalog unavailable" : "Connecting"}</span><button className="icon-button" onClick={() => setAssistant(true)} aria-label="Open AI assistant"><Bot /></button><button className="cart-button" onClick={() => setCheckout(true)} aria-label="Open cart"><ShoppingBag /><b>{cart.reduce((n, item) => n + item.quantity, 0)}</b></button><button className="menu-button" aria-label="Open menu"><Menu /></button></div></header>
    <main id="top">
      <section className="hero"><div className="hero-copy"><motion.p initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="kicker"><Sparkles /> Your smarter way to shop</motion.p><motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .08 }} >Shop smarter with an AI that <em>gets you.</em></motion.h1><p className="hero-text">Tell us what you&apos;re looking for. nura finds the right products, secures your price, and helps you check out safely.</p><div className="hero-actions"><button className="primary-button" onClick={() => document.getElementById("shop")?.scrollIntoView({ behavior: "smooth" })}>Start shopping <ArrowRight /></button><button className="text-button" onClick={() => setAssistant(true)}><Bot /> Ask nura</button></div><div className="hero-proof"><span><ShieldCheck /> Protected checkout</span><span><Star /> 4.9 customer rating</span></div></div><motion.div className="hero-art" initial={{ opacity: 0, scale: .96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: .7 }}>{products[0]?.image ? <img src={products[0].image} alt="Camera ready for a creative shoot" /> : <div className="hero-art-placeholder"><ShoppingBag /><span>{catalogLoading ? "Loading the live catalog..." : "The catalog is ready for your products."}</span></div>}<div className="floating-note"><span className="note-icon"><Sparkles /></span><div><strong>Made for your setup</strong><small>AI matched 3 essentials</small></div><Check /></div><div className="art-stamp">NURA<br /><small>CURATED / 01</small></div></motion.div></section>
      <section className="trust-strip"><div><ShieldCheck /><span><strong>Human-first AI</strong><small>Recommendations with a reason</small></span></div><div><Clock3 /><span><strong>Price protection</strong><small>Lock your quote for 15 minutes</small></span></div><div><ShoppingBag /><span><strong>Secure checkout</strong><small>Protected by our commerce gateway</small></span></div></section>
      <section className="shop-section" id="shop"><div className="section-heading"><div><p className="eyebrow">THE EDIT / 01</p><h2>Find your next favorite thing.</h2></div><button className="outline-button" onClick={() => setAssistant(true)}>Let AI choose for me <Sparkles /></button></div><div className="shop-controls"><label className="search-box"><Search /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search the edit..." /></label><div className="category-tabs">{categories.map((item) => <button className={category === item ? "active" : ""} key={item} onClick={() => setCategory(item)}>{item}</button>)}</div><button className="filter-button">Filter <ChevronDown /></button></div><div className="product-grid">{filtered.map((product, index) => <motion.article key={product.id} className="product-card" initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: index * .05 }}><div className="product-image">{product.image ? <img src={product.image} alt={product.name} /> : <div className="product-image-placeholder"><ShoppingBag /></div>}<button className="heart-button" aria-label={`Save ${product.name}`}><Heart /></button><span className="product-badge">{index === 0 ? "AI pick" : "In stock"}</span></div><div className="product-info"><div className="product-meta"><span>{product.category}</span><span><Star /> {product.rating}</span></div><h3>{product.name}</h3><p>{product.description}</p><div className="product-bottom"><strong>{money(product.price)}</strong><button onClick={() => setSelected(product)}>View product <ArrowRight /></button></div></div></motion.article>)}</div>{!catalogLoading && (catalogError || products.length === 0) && <div className="catalog-empty"><ShoppingBag /><p>{catalogError ?? "No products in the live catalog yet."}</p><span>{catalogError ? "Check the API connection and refresh to try again." : "Add a product from the Gateway to begin."}</span></div>}</section>
      <section className="ai-banner"><div><p className="eyebrow">A PERSONAL SHOPPER IN YOUR POCKET</p><h2>Good shopping starts with a good question.</h2><p>Not sure what you need? Describe the setup, the budget, or the feeling. nura will do the browsing.</p><button className="cream-button" onClick={() => setAssistant(true)}>Ask nura anything <ArrowRight /></button></div><div className="ai-orbit"><Bot /><span /><span /><span /></div></section>
      <section className="protected" id="protected"><div><p className="eyebrow">BUILT INTO EVERY PURCHASE</p><h2>Technology you can trust.<br /><em>Without the jargon.</em></h2><p>Every nura recommendation passes through a secure commerce gateway that protects your price, your payment, and your peace of mind.</p><button className="text-button" onClick={() => setShowTrust(!showTrust)}>See how it works <ArrowRight /></button></div><div className="flow">{["AI understands", "Price secured", "Safety checked", "Payment protected"].map((step, i) => <div className="flow-step" key={step}><span>0{i + 1}</span><strong>{step}</strong>{i < 3 && <ArrowRight />}</div>)}</div></section>
    </main>
    <footer><a className="logo" href="#top"><span className="logo-dot" />nura</a><span>Thoughtful commerce, powered by AI.</span><span>© 2025 nura</span></footer>

    <AnimatePresence>{selected && <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><motion.div className="detail-drawer" initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}><button className="close-button" onClick={() => setSelected(null)} aria-label="Close product"><X /></button>{selected.image ? <img className="drawer-image" src={selected.image} alt={selected.name} /> : <div className="drawer-image-placeholder"><ShoppingBag /></div>}<div className="drawer-copy"><p className="eyebrow">{selected.category}</p><h2>{selected.name}</h2><div className="drawer-rating"><Star /> {selected.rating} · Loved by creators</div><p>{selected.description} Designed to work beautifully with the way you already create.</p><div className="detail-row"><span>Price</span><strong>{money(selected.price)}</strong></div><div className="detail-row"><span>Delivery</span><strong>{selected.delivery}</strong></div><div className="detail-row"><span>Compatibility</span><strong>{selected.compatibility}</strong></div>{quoteError && <p className="quote-error" role="alert">{quoteError}</p>}<button className="primary-button full" disabled={quoteBusy} onClick={() => void requestQuote(selected).catch(() => undefined)}>{quoteBusy ? "Securing your price..." : "Get a locked quote"} <ShieldCheck /></button><button className="outline-button full" onClick={() => { addToCart(selected); setSelected(null); }}>Add to cart</button></div></motion.div></motion.div>}</AnimatePresence>
    <AnimatePresence>{quote && selected && <motion.div className="modal-wrap" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><motion.div className="quote-modal" initial={{ y: 20, scale: .97 }} animate={{ y: 0, scale: 1 }}><div className="success-icon"><ShieldCheck /></div><p className="eyebrow">YOUR PRICE IS SECURED</p><h2>Locked in.</h2><p>Your price for {selected.name} is protected for 15 minutes.</p><strong className="quote-price">{money(quote.locked_price_paise)}</strong><div className="quote-timer"><Clock3 /> Expires soon · <b>14:59</b></div>{upsell && <div className="upsell"><Sparkles /><div><strong>Complete your setup?</strong><p>{upsell.suggested_item} — {upsell.reason}</p></div><button onClick={() => { const match = products.find((p) => p.name === upsell.suggested_item); if (match) addToCart(match); }}>Add</button></div>}<button className="primary-button full" onClick={() => { addToCart(selected, quote.quantity); setQuote(null); setSelected(null); setCheckout(true); }}>Continue to checkout <ArrowRight /></button><button className="quiet-button" onClick={() => { setQuote(null); setSelected(null); }}>Not now</button></motion.div></motion.div>}</AnimatePresence>
    <AnimatePresence>{checkout && <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><motion.div className="checkout-drawer" initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}><button className="close-button" onClick={() => setCheckout(false)} aria-label="Close checkout"><X /></button>{payment === "idle" || checkoutError ? <><p className="eyebrow">SECURE CHECKOUT</p><h2>{checkoutError ? "Checkout needs attention." : "Ready when you are."}</h2>{checkoutError ? <><p className="checkout-error" role="alert">{checkoutError}</p><button className="primary-button full" onClick={() => { setCheckoutError(null); const item = cart[0]; if (item) void requestQuote(item.product).then(() => startCheckout()).catch(() => undefined); }}>Retry checkout <ArrowRight /></button></> : <>{cart.length ? <div className="bag-list">{cart.map((item) => <div className="bag-item" key={item.product.id}>{item.product.image ? <img src={item.product.image} alt="" /> : <div className="bag-image-placeholder"><ShoppingBag /></div>}<div><strong>{item.product.name}</strong><small>Qty {item.quantity}</small></div><b>{money(item.product.price * item.quantity)}</b></div>)}</div> : <div className="empty-bag"><ShoppingBag /><p>Your bag is waiting for something good.</p><button className="text-button" onClick={() => setCheckout(false)}>Continue shopping <ArrowRight /></button></div>}<div className="total-row"><span>Total</span><strong>{money(total)}</strong></div><button className="primary-button full" disabled={!cart.length} onClick={async () => { const item = cart[0]; if (item) { try { await requestQuote(item.product); await startCheckout(); } catch { setCheckoutError("The quote could not be created. Check stock and try again."); } } }}>Continue to secure checkout <ArrowRight /></button></>}</> : <><p className="eyebrow">SECURE CHECKOUT</p><h2>{payment === "approval" ? "A quick approval is needed." : payment === "ready" ? "You&apos;re ready to pay." : payment === "failed" ? "Payment could not be prepared." : "Your order is protected."}</h2><p>{payment === "approval" ? "This purchase is above the automatic spending limit. We&apos;re waiting for merchant approval before payment can continue." : payment === "failed" ? "The payment provider did not accept this request. No payment was made." : "Your order is secured by the nura commerce gateway. No surprises, just a safe way to finish."}</p><div className={`checkout-state ${payment}`}><ShieldCheck /><strong>{payment === "approval" ? "Approval requested" : payment === "ready" ? "Approved — continue to payment" : payment === "failed" ? "Payment unavailable" : "Payment required"}</strong><span>{payment === "approval" ? "Waiting for approval..." : payment === "ready" ? "Razorpay test mode is ready" : payment === "failed" ? "Try again later" : "Continue securely with Razorpay"}</span></div>{payment === "approval" ? <button className="primary-button full" onClick={() => setPayment("ready")}>Simulate approval <ArrowRight /></button> : payment === "ready" ? <button className="primary-button full" onClick={() => { setPayment("idle"); setCheckout(false); setOrder(null); setCart([]); setSelected(null); setAssistant(false); alert("Purchase confirmed — thank you for shopping with nura."); }}>Pay securely with Razorpay <ArrowRight /></button> : payment === "failed" ? <button className="primary-button full" onClick={() => setPayment("pending")}>Retry payment <ArrowRight /></button> : <button className="primary-button full" onClick={createPayment}>Continue to payment <ArrowRight /></button>}<button className="quiet-button" onClick={() => setCheckout(false)}>Save for later</button></>}</motion.div></motion.div>}</AnimatePresence>
    <AnimatePresence>{assistant && <motion.div className="assistant" initial={{ opacity: 0, y: 20, scale: .96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 20, scale: .96 }}><div className="assistant-head"><div><span className="ai-avatar"><Bot /></span><div><strong>nura AI</strong><small>Your personal shopper</small></div></div><button onClick={() => setAssistant(false)} aria-label="Close assistant"><X /></button></div><div className="assistant-body"><div className="ai-message">Hi, I&apos;m nura. What are you looking to find today?</div><div className="suggestions"><button onClick={() => setAssistantText("I need a camera accessory under ₹2,000")}>Camera accessories under ₹2,000</button><button onClick={() => setAssistantText("Help me complete my setup")}>Help me complete my setup</button></div>{assistantText && bestMatch && <><div className="user-message">{assistantText}</div><div className="ai-message">I found {filtered.slice(0, 3).length} options that match. I&apos;d start with the <strong>{bestMatch.name}</strong> — it&apos;s a great fit for your needs.</div><button className="assistant-result" onClick={() => { setAssistant(false); setSelected(bestMatch); }}>{bestMatch.image ? <img src={bestMatch.image} alt="" /> : <span className="assistant-image-placeholder"><ShoppingBag /></span>}<span>View my best match <ArrowRight /></span></button></>}</div><div className="assistant-input"><input value={assistantText} onChange={(e) => setAssistantText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && setAssistantText(e.currentTarget.value)} placeholder="Tell me what you need..." /><button aria-label="Send" onClick={() => setAssistantText(assistantText || "Show me your best picks")}><ArrowRight /></button></div></motion.div>}</AnimatePresence>
    {showTrust && <div className="toast-trust"><ShieldCheck /> Your purchase is protected end to end.</div>}
  </div>;
}
