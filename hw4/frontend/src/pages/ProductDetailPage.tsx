import { useEffect, useMemo, useState, type CSSProperties, type MouseEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  categoryLabel,
  categoryOf,
  fetchProduct,
  fetchProducts,
  formatPrice,
  LOW_STOCK,
  type ProductDetail,
  type ProductSummary,
} from "../api";
import { openChat } from "../chatEvents";
import { swatch } from "../colors";
import ProductCard from "../components/ProductCard";
import ProductImage from "../components/ProductImage";
import { ErrorMessage } from "../components/Status";

function stockText(quantity: number) {
  if (quantity === 0) return "Sold out";
  if (quantity <= LOW_STOCK) return `Only ${quantity} left`;
  return `${quantity} in stock`;
}

export default function ProductDetailPage() {
  const { productId = "" } = useParams();
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedSize, setSelectedSize] = useState<string | null>(null);
  const [related, setRelated] = useState<ProductSummary[]>([]);
  // Hover zoom on the photo: magnify around the pointer (desktop only; see .detail-image in index.css).
  const [zoom, setZoom] = useState<{ x: number; y: number } | null>(null);
  const onZoomMove = (e: MouseEvent<HTMLDivElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    setZoom({ x: ((e.clientX - box.left) / box.width) * 100, y: ((e.clientY - box.top) / box.height) * 100 });
  };

  const load = () => {
    setProduct(null);
    setError(null);
    setSelectedSize(null);
    fetchProduct(productId)
      .then(setProduct)
      .catch((e: Error) => setError(e.message === "not-found" ? "not-found" : "We couldn't load this product."));
  };
  useEffect(load, [productId]);

  useEffect(() => {
    fetchProducts().then(setRelated).catch(() => setRelated([]));
  }, []);

  const alsoLike = useMemo(() => {
    if (!product) return [];
    const cat = categoryOf(product.garment_type);
    return related.filter((p) => p.product_id !== product.product_id && categoryOf(p.garment_type) === cat).slice(0, 4);
  }, [product, related]);

  if (error === "not-found") {
    return (
      <div className="container page">
        <div className="status-box">
          <p className="status-title">Product not found</p>
          <p>This item may have moved. Browse the full collection instead.</p>
          <Link to="/products" className="btn btn-primary">
            Shop All
          </Link>
        </div>
      </div>
    );
  }
  if (error) return <div className="container page"><ErrorMessage message={error} onRetry={load} /></div>;
  if (!product) {
    return (
      <div className="container page">
        <div className="detail skeleton" aria-busy="true" aria-label="Loading product">
          <div className="detail-image" />
          <div className="detail-info">
            <div className="skeleton-line short" />
            <div className="skeleton-line" />
            <div className="skeleton-line" />
          </div>
        </div>
      </div>
    );
  }

  const category = categoryOf(product.garment_type);
  const selected = product.inventory.find((s) => s.size === selectedSize);
  const sizesInStock = product.inventory.filter((s) => s.in_stock).length;

  return (
    <div className="container page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <span aria-hidden="true">/</span>
        <Link to="/products">Shop All</Link>
        <span aria-hidden="true">/</span>
        <Link to={`/products?category=${category}`}>{categoryLabel(category)}</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{product.name}</span>
      </nav>

      <article className="detail">
        <div className="detail-gallery">
          <div
            className={`detail-image ${zoom ? "is-zoomed" : ""}`}
            onMouseMove={onZoomMove}
            onMouseLeave={() => setZoom(null)}
            style={zoom ? ({ "--zoom-x": `${zoom.x}%`, "--zoom-y": `${zoom.y}%` } as CSSProperties) : undefined}
          >
            <ProductImage src={product.image_url} alt={product.name} loading="eager" />
          </div>
          <p className="detail-zoom-hint" aria-hidden="true">Hover to zoom</p>
        </div>

        <div className="detail-info">
          <p className="eyebrow">{categoryLabel(category)}</p>
          <h1 className="detail-name">{product.name}</h1>
          <div className="detail-price-row">
            <p className="detail-price">{formatPrice(product.price)}</p>
            <span className={`stock-pill ${product.total_stock === 0 ? "is-out" : sizesInStock < product.inventory.length ? "is-partial" : ""}`}>
              {product.total_stock === 0 ? "Sold out" : sizesInStock < product.inventory.length ? "Limited sizes" : "In stock"}
            </span>
          </div>

          <p className="detail-description">{product.description}</p>

          <div className="detail-block">
            <p className="detail-label">
              Color{product.colors.length === 1 ? "" : "s"}
            </p>
            <ul className="color-list">
              {product.colors.map((c) => (
                <li key={c} className="color-chip">
                  <span className="swatch" style={{ background: swatch(c) }} aria-hidden="true" />
                  {c}
                </li>
              ))}
            </ul>
          </div>

          <div className="detail-block">
            <div className="detail-label-row">
              <p className="detail-label">Size</p>
              <p className="detail-stock-summary">
                {product.total_stock} in stock across {sizesInStock} of {product.inventory.length} sizes
              </p>
            </div>
            <div className="size-grid" role="radiogroup" aria-label="Choose a size">
              {product.inventory.map((s) => (
                <button
                  key={s.size}
                  role="radio"
                  aria-checked={selectedSize === s.size}
                  className={`size-option ${selectedSize === s.size ? "selected" : ""} ${s.in_stock ? "" : "sold-out"} ${
                    s.in_stock && s.quantity <= LOW_STOCK ? "low" : ""
                  }`}
                  disabled={!s.in_stock}
                  onClick={() => setSelectedSize(s.size)}
                >
                  <span className="size-name">{s.size}</span>
                  <span className="size-stock">{stockText(s.quantity)}</span>
                </button>
              ))}
            </div>
            <p className="selected-size" aria-live="polite">
              {selected ? `Size ${selected.size}: ${stockText(selected.quantity)}` : "Select a size to see its availability."}
            </p>
          </div>

          <button className="btn btn-primary btn-block btn-lg" disabled>
            Add to Bag · Online checkout coming soon
          </button>
          <button className="btn btn-outline btn-block" onClick={() => openChat()}>
            <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M21 12a8 8 0 0 1-11.8 7L4 20l1.1-4.6A8 8 0 1 1 21 12z" strokeLinejoin="round" />
            </svg>
            Ask the assistant about this item
          </button>

          <ul className="detail-assurances">
            <li>
              <strong>Live stock</strong>
              <span>Counts update from our inventory</span>
            </li>
            <li>
              <strong>XS to XXL</strong>
              <span>Every size listed above</span>
            </li>
            <li>
              <strong>{product.garment_type}</strong>
              <span>Style</span>
            </li>
          </ul>
        </div>
      </article>

      {alsoLike.length > 0 && (
        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Complete the look</p>
              <h2>You may also like</h2>
            </div>
            <Link to={`/products?category=${category}`} className="text-link">
              More {categoryLabel(category)} →
            </Link>
          </div>
          <div className="product-grid">
            {alsoLike.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
