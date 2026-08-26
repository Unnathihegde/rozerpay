import { useState } from "react";
import type { FormEvent } from "react";
import { createProduct } from "./api";

export default function AddProduct() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [price, setPrice] = useState(0); // rupees
  const [stock, setStock] = useState(1);
  const [attributes, setAttributes] = useState("{}");
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      let parsedAttrs: Record<string, unknown> = {};
      try {
        parsedAttrs = attributes ? JSON.parse(attributes) : {};
      } catch (err) {
        alert("Attributes must be valid JSON");
        setLoading(false);
        return;
      }
      const payload = {
        name,
        category,
        price_paise: Math.round(price * 100),
        stock_qty: stock,
        attributes: parsedAttrs,
      };
      await createProduct(payload);
      alert("Product created successfully. Refreshing catalog...");
      window.location.reload();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error(err);
      alert("Failed to create product");
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <div style={{ display: "inline-block", marginLeft: 12 }}>
        <button className="gateway-add-product" onClick={() => setOpen(true)}>Add Product</button>
      </div>
    );
  }

  return (
    <div className="add-product-form" style={{ padding: 12, background: "#fff", borderRadius: 8, marginLeft: 12 }}>
      <form onSubmit={submit}>
        <div style={{ display: "flex", gap: 8 }}>
          <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
          <input placeholder="Category" value={category} onChange={(e) => setCategory(e.target.value)} required />
          <input type="number" step="0.01" placeholder="Price (₹)" value={price} onChange={(e) => setPrice(Number(e.target.value))} required />
          <input type="number" placeholder="Stock" value={stock} onChange={(e) => setStock(Number(e.target.value))} required />
        </div>
        <div style={{ marginTop: 8 }}>
          <textarea rows={3} placeholder='Attributes (JSON), e.g. {"compatibility":"USB-C"}' value={attributes} onChange={(e) => setAttributes(e.target.value)} />
        </div>
        <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
          <button type="submit" disabled={loading}>Create</button>
          <button type="button" onClick={() => setOpen(false)}>Cancel</button>
        </div>
      </form>
    </div>
  );
}
