import { Link } from "react-router-dom";
import { categoryLabel, categoryOf, formatPrice, LOW_STOCK, type ProductSummary } from "../api";
import { swatch } from "../colors";
import ProductImage from "./ProductImage";

export default function ProductCard({ product }: { product: ProductSummary }) {
  const soldOut = product.total_stock === 0;
  const low = !soldOut && product.total_stock <= LOW_STOCK;
  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card-media">
        <ProductImage src={product.image_url} alt={product.name} className="product-card-image" />
        {(soldOut || low) && <span className={`product-badge ${soldOut ? "is-sold-out" : ""}`}>{soldOut ? "Sold out" : "Low stock"}</span>}
        <span className="product-card-cta" aria-hidden="true">
          View details <span className="arrow">→</span>
        </span>
      </div>
      <div className="product-card-body">
        <p className="product-card-category">{categoryLabel(categoryOf(product.garment_type))}</p>
        <h3 className="product-card-name">{product.name}</h3>
        <p className="product-card-description">{product.description}</p>
        <div className="product-card-footer">
          <p className="product-card-price">{formatPrice(product.price)}</p>
          {product.colors.length > 0 && (
            <ul className="swatches" aria-label={`Colors: ${product.colors.join(", ")}`}>
              {product.colors.slice(0, 4).map((c) => (
                <li key={c} className="swatch" style={{ background: swatch(c) }} title={c} />
              ))}
              {product.colors.length > 4 && <li className="swatch-more">+{product.colors.length - 4}</li>}
            </ul>
          )}
        </div>
      </div>
    </Link>
  );
}
