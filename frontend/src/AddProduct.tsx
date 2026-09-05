import { useState } from "react";
import type { FormEvent } from "react";
import { createProduct } from "./api";

export default function AddProduct() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [price, setPrice] = useState(0); // rupees
  const [stock, setStock] = useState(1);
  const [imageUrl, setImageUrl] = useState("");
  const [attributes, setAttributes] = useState("{}");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      let parsedAttrs: Record<string, unknown> = {};
      try {
        parsedAttrs = attributes ? JSON.parse(attributes) : {};
      } catch {
        setError("Attributes must be valid JSON.");
        setLoading(false);
        return;
      }
      const payload = {
        name,
        category,
        price_paise: Math.round(price * 100),
        stock_qty: stock,
        image_url: imageUrl.trim() || undefined,
        attributes: parsedAttrs,
      };
      await createProduct(payload);
      alert("Product created successfully. Refreshing catalog...");
      window.location.reload();
    } catch {
      setError("Product could not be created. Check the connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <div className="add-product-trigger">
        <button className="gateway-add-product" onClick={() => setOpen(true)}>Add Product</button>
      </div>
    );
  }

  return (
    <div className="add-product-form">
      <div className="add-product-heading"><div><span className="add-product-kicker">Catalog</span><h2>Add product</h2></div><button type="button" className="add-product-close" onClick={() => setOpen(false)} aria-label="Close add product form">×</button></div>
      <form onSubmit={submit}>
        <div className="add-product-fields">
          <label>Product name<input placeholder="e.g. USB-C cable" value={name} onChange={(e) => setName(e.target.value)} required /></label>
          <label>Category<input placeholder="e.g. accessory" value={category} onChange={(e) => setCategory(e.target.value)} required /></label>
          <label>Price (INR)<input type="number" min="0.01" step="0.01" placeholder="0.00" value={price || ""} onChange={(e) => setPrice(Number(e.target.value))} required /></label>
          <label>Stock quantity<input type="number" min="0" step="1" placeholder="0" value={stock} onChange={(e) => setStock(Number(e.target.value))} required /></label>
          <label>Image URL<input type="url" placeholder="https://example.com/product.jpg" value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} /></label>
        </div>
        <label className="add-product-attributes">Attributes <span>Optional JSON metadata</span><textarea rows={4} placeholder='{"compatibility":"USB-C"}' value={attributes} onChange={(e) => setAttributes(e.target.value)} /></label>
        {error && <p className="add-product-error" role="alert">{error}</p>}
        <div className="add-product-actions">
          <button className="add-product-submit" type="submit" disabled={loading}>{loading ? "Creating..." : "Create product"}</button>
          <button className="add-product-cancel" type="button" onClick={() => setOpen(false)}>Cancel</button>
        </div>
      </form>
    </div>
  );
}
