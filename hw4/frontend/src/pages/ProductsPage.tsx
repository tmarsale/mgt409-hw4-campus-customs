import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CATEGORIES, categoryOf, fetchAssistantResults, fetchProducts, type CategorySlug, type ProductSummary } from "../api";
import { useAssistantResults } from "../assistantResults";
import ProductCard from "../components/ProductCard";
import { ErrorMessage, LoadingGrid } from "../components/Status";

type Sort = "name" | "price-asc" | "price-desc";

export default function ProductsPage() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [params, setParams] = useSearchParams();
  const { results: assistantResults, show: showAssistantResults, clear: clearAssistantResults } = useAssistantResults();

  const category = (params.get("category") ?? "") as CategorySlug | "";
  // The search box keeps its own text and copies it to the address (?search=), instead of reading
  // it back from the address on every keystroke: the address updates a moment later, and fast
  // typing used to lose letters ("navy" became "y").
  const urlSearch = params.get("search") ?? "";
  const [search, setSearch] = useState(urlSearch);
  const typed = useRef(new Set<string>()); // values this box wrote to the address
  useEffect(() => {
    // Follow outside changes to the address (Clear filters, Back/Forward), not our own updates
    // arriving late.
    if (typed.current.has(urlSearch)) return;
    typed.current.clear();
    setSearch(urlSearch);
  }, [urlSearch]);
  const sort = (params.get("sort") ?? "name") as Sort;

  const load = () => {
    setError(null);
    fetchProducts().then(setProducts).catch(() => setError("We couldn't load our products. Please try again."));
  };
  useEffect(load, []);

  const clearFilters = () => {
    typed.current.clear();
    setSearch("");
    setParams({}, { replace: true });
  };

  const update = (key: string, value: string) => {
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );
  };

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    const list = (products ?? []).filter((p) => {
      if (category && categoryOf(p.garment_type) !== category) return false;
      if (!term) return true;
      // Same fields the backend's search uses: name, type, description, colors, and search tags.
      return [p.name, p.garment_type, p.description, ...p.colors, ...p.search_tags].some((field) =>
        field.toLowerCase().includes(term),
      );
    });
    if (sort === "price-asc") list.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name));
    else if (sort === "price-desc") list.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name));
    else list.sort((a, b) => a.name.localeCompare(b.name));
    return list;
  }, [products, category, search, sort]);

  const title = CATEGORIES.find((c) => c.slug === category)?.label ?? "Shop All";

  // Products found by the shopping assistant (Problem 7), shown with the same cards as the shop.
  const assistantView = params.get("view") === "assistant";
  const assistantQuery = params.get("q") ?? "";
  // Problem 9: the search is in the address (?q=), so after a refresh (or from a bookmark) the
  // same results are fetched again from the backend instead of disappearing.
  const needsRefetch = assistantView && assistantQuery !== "" && assistantResults?.query !== assistantQuery;
  const [refetchError, setRefetchError] = useState(false);
  const [refetchAttempt, setRefetchAttempt] = useState(0);
  useEffect(() => {
    if (!needsRefetch) return;
    let cancelled = false;
    setRefetchError(false);
    fetchAssistantResults(assistantQuery)
      .then((r) => !cancelled && showAssistantResults(r))
      .catch(() => !cancelled && setRefetchError(true));
    return () => {
      cancelled = true;
    };
  }, [needsRefetch, assistantQuery, showAssistantResults, refetchAttempt]);

  const showAll = () => {
    clearAssistantResults();
    clearFilters();
  };

  if (needsRefetch) {
    return (
      <div className="container page">
        <header className="page-header">
          <p className="eyebrow">From the Shopping Assistant</p>
          <h1>Results for “{assistantQuery}”</h1>
        </header>
        {refetchError ? (
          <ErrorMessage message="We couldn't load these results. Please try again." onRetry={() => setRefetchAttempt((n) => n + 1)} />
        ) : (
          <LoadingGrid />
        )}
      </div>
    );
  }
  if (assistantView && assistantResults && assistantResults.total === 0) {
    return (
      <div className="container page">
        <header className="page-header">
          <p className="eyebrow">From the Shopping Assistant</p>
          <h1>No matching products</h1>
        </header>
        <div className="status-box" role="status">
          <p className="status-title">Nothing matched “{assistantResults.query}”</p>
          <p>We couldn't find products for that request. Try asking the assistant for something else, or browse everything we carry.</p>
          <button className="btn btn-primary" onClick={showAll}>
            Show all products
          </button>
        </div>
      </div>
    );
  }
  if (assistantView && assistantResults) {
    const { query, total, products: found } = assistantResults;
    return (
      <div className="container page">
        <header className="page-header">
          <p className="eyebrow">From the Shopping Assistant</p>
          <h1>Results for “{query}”</h1>
        </header>
        <div className="assistant-results-banner" role="status">
          <p>
            <span className="assistant-results-label">
              <svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12a8 8 0 0 1-11.8 7L4 20l1.1-4.6A8 8 0 1 1 21 12z" strokeLinejoin="round" />
              </svg>
              Found by the assistant
            </span>
            <br />
            {total} matching {total === 1 ? "product" : "products"}
            {found.length < total ? ` (showing the first ${found.length})` : ""}. Select one for sizes and stock.
          </p>
          <button className="btn btn-outline btn-sm" onClick={showAll}>
            Show all products
          </button>
        </div>
        <div className="product-grid">
          {found.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="container page">
      <header className="page-header">
        <p className="eyebrow">Campus Customs Shop</p>
        <h1>{title}</h1>
        <p className="page-intro">Yale hoodies, crewnecks, tees, and more, in sizes XS to XXL.</p>
      </header>

      <div className="filters">
        <div className="chip-row" role="group" aria-label="Filter by category">
          <button className={`chip ${category === "" ? "active" : ""}`} onClick={() => update("category", "")}>
            All
          </button>
          {CATEGORIES.map((c) => (
            <button key={c.slug} className={`chip ${category === c.slug ? "active" : ""}`} onClick={() => update("category", c.slug)}>
              {c.label}
            </button>
          ))}
        </div>
        <div className="filter-controls">
          <label className="search-field">
            <span className="visually-hidden">Search products</span>
            <input
              type="search"
              placeholder="Search by name, color, or style"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                typed.current.add(e.target.value);
                update("search", e.target.value);
              }}
            />
          </label>
          <label className="sort-field">
            <span>Sort</span>
            <select value={sort} onChange={(e) => update("sort", e.target.value === "name" ? "" : e.target.value)}>
              <option value="name">Name (A–Z)</option>
              <option value="price-asc">Price: low to high</option>
              <option value="price-desc">Price: high to low</option>
            </select>
          </label>
        </div>
      </div>

      {error ? (
        <ErrorMessage message={error} onRetry={load} />
      ) : products === null ? (
        <LoadingGrid />
      ) : (
        <>
          <p className="result-count" aria-live="polite">
            {visible.length} {visible.length === 1 ? "product" : "products"}
          </p>
          {visible.length > 0 ? (
            <div className="product-grid">
              {visible.map((p) => (
                <ProductCard key={p.product_id} product={p} />
              ))}
            </div>
          ) : (
            <div className="status-box">
              <p className="status-title">No products match your search</p>
              <p>Try a different word or browse all categories.</p>
              <button className="btn btn-outline" onClick={clearFilters}>
                Clear filters
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
