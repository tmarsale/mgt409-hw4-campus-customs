import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { CATEGORIES, categoryOf, fetchProducts, formatPrice, type ProductSummary } from "../api";
import { assistantViewUrl } from "../assistantResults";
import { useAuth } from "../auth";
import { openChat } from "../chatEvents";
import ProductCard from "../components/ProductCard";
import ProductImage from "../components/ProductImage";
import Reveal from "../components/Reveal";
import { ErrorMessage, LoadingGrid } from "../components/Status";

const MARQUEE = ["Residential colleges", "Game day", "Gifts for Mom & Dad", "Alumni classics", "Quarter-zips", "Heavyweight crewnecks", "Fleece for winter"];

const ASK_EXAMPLES = ["Something cozy for winter", "A gift for my dad", "Show me quarter-zips", "Game-day T-shirts"];

const PROMISES = [
  { icon: "M4 7h16M4 12h16M4 17h10", title: "Live stock, every size", text: "See exactly how many are left in XS to XXL before you choose." },
  { icon: "M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z", title: "Every college & team", text: "Residential colleges, schools, and Yale athletics in one place." },
  { icon: "M20 12v9H4v-9M2 7h20v5H2zM12 21V7M12 7c-2-4-6-4-6-1s6 1 6 1zm0 0c2-4 6-4 6-1s-6 1-6 1z", title: "Gifts for the family", text: "Mom, Dad, Grandpa, and more, all in Yale blue." },
  { icon: "M21 12a8 8 0 0 1-11.8 7L4 20l1.1-4.6A8 8 0 1 1 21 12z", title: "Help when you want it", text: "Our shopping assistant answers sizing, color, and stock questions." },
];

export default function HomePage() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();
  const location = useLocation();
  const [welcome, setWelcome] = useState(Boolean((location.state as { welcome?: boolean } | null)?.welcome));

  const load = () => {
    setError(null);
    fetchProducts().then(setProducts).catch(() => setError("We couldn't load our products right now."));
  };
  useEffect(load, []);

  // Everything shown here is picked from the real catalogue: for each category, the
  // best-stocked item represents it, and the featured picks are one per category.
  const byCategory = useMemo(() => {
    const groups = new Map<string, ProductSummary[]>();
    for (const p of products ?? []) {
      const key = categoryOf(p.garment_type);
      groups.set(key, [...(groups.get(key) ?? []), p]);
    }
    for (const list of groups.values()) list.sort((a, b) => b.total_stock - a.total_stock);
    return groups;
  }, [products]);

  const featured = CATEGORIES.slice(0, 4)
    .map((c) => byCategory.get(c.slug)?.[0])
    .filter((p): p is ProductSummary => Boolean(p));
  const family = (products ?? []).filter((p) => /\b(mom|dad|grandpa|grandma|aunt|uncle|brother|sister|cousin)\b/i.test(p.name)).slice(0, 4);
  const heroMain = byCategory.get("hoodies")?.[0];
  const heroSide = [byCategory.get("quarter-zips")?.[0], byCategory.get("tees")?.[0]].filter((p): p is ProductSummary => Boolean(p));

  return (
    <>
      {welcome && user && (
        <div className="welcome-banner" role="status">
          <div className="container welcome-inner">
            <p>
              Welcome, <strong>{user.first_name}</strong>! You're signed in to Campus Customs.
            </p>
            <button className="welcome-close" onClick={() => setWelcome(false)} aria-label="Dismiss welcome message">
              ×
            </button>
          </div>
        </div>
      )}

      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-copy">
            <p className="eyebrow">Yale apparel &amp; gifts · New Haven</p>
            <h1>
              Dressed in <em>Yale blue</em>, made for every Bulldog.
            </h1>
            <p className="hero-text">
              Game-day hoodies, residential college crewnecks, and gifts for the whole family, with live stock for every
              size so you know exactly what's ready to wear.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="btn btn-primary btn-lg">
                Shop the Collection <span className="arrow">→</span>
              </Link>
              <button className="btn btn-outline btn-lg" onClick={() => openChat()}>
                Ask our assistant
              </button>
            </div>
            <dl className="hero-stats">
              <div>
                <dt>Styles</dt>
                <dd>{products ? products.length : "—"}</dd>
              </div>
              <div>
                <dt>Categories</dt>
                <dd>{CATEGORIES.length}</dd>
              </div>
              <div>
                <dt>Sizes</dt>
                <dd>XS–XXL</dd>
              </div>
            </dl>
          </div>

          <div className="hero-media" role="group" aria-label="Featured products">
            {heroMain ? (
              <>
                <Link to={`/products/${heroMain.product_id}`} className="hero-tile hero-tile-main">
                  <ProductImage src={heroMain.image_url} alt={heroMain.name} loading="eager" />
                  <span className="hero-tag">
                    <span className="hero-tag-label">Fan favorite</span>
                    <span className="hero-tag-name">{heroMain.name}</span>
                    <span className="hero-tag-price">{formatPrice(heroMain.price)}</span>
                  </span>
                </Link>
                {heroSide.map((p, i) => (
                  <Link key={p.product_id} to={`/products/${p.product_id}`} className={`hero-tile hero-tile-side hero-tile-${i + 1}`}>
                    <ProductImage src={p.image_url} alt={p.name} loading="eager" />
                  </Link>
                ))}
                <span className="hero-seal" aria-hidden="true">
                  <svg viewBox="0 0 100 100">
                    <defs>
                      <path id="seal-circle" d="M50 50m-36 0a36 36 0 1 1 72 0a36 36 0 1 1-72 0" />
                    </defs>
                    <text>
                      <textPath href="#seal-circle">CAMPUS CUSTOMS · NEW HAVEN · YALE BLUE ·</textPath>
                    </text>
                  </svg>
                  <span>CC</span>
                </span>
              </>
            ) : (
              <div className="hero-tile hero-tile-main placeholder" aria-hidden="true" />
            )}
          </div>
        </div>
      </section>

      <div className="marquee" aria-hidden="true">
        <div className="marquee-track">
          {[...MARQUEE, ...MARQUEE].map((word, i) => (
            <span key={i}>
              {word} <span className="marquee-dot">✦</span>
            </span>
          ))}
        </div>
      </div>

      <section className="section container">
        <Reveal>
          <div className="section-heading">
            <div>
              <p className="eyebrow">Find your fit</p>
              <h2>Shop by Category</h2>
            </div>
            <Link to="/products" className="text-link">
              View all <span className="arrow">→</span>
            </Link>
          </div>
        </Reveal>
        {error ? (
          <ErrorMessage message={error} onRetry={load} />
        ) : (
          <div className="category-grid">
            {CATEGORIES.map((c, i) => {
              const items = byCategory.get(c.slug);
              return (
                <Reveal key={c.slug} delay={i * 60}>
                  <Link to={`/products?category=${c.slug}`} className="category-tile">
                    {items?.[0] ? (
                      <ProductImage src={items[0].image_url} alt="" className="category-tile-image" />
                    ) : (
                      <div className="photo category-tile-image" />
                    )}
                    <span className="category-tile-text">
                      <span className="category-tile-name">{c.label}</span>
                      <span className="category-tile-count">{items ? `${items.length} styles` : " "}</span>
                    </span>
                  </Link>
                </Reveal>
              );
            })}
          </div>
        )}
      </section>

      <section className="section section-tinted">
        <div className="container">
          <Reveal>
            <div className="section-heading">
              <div>
                <p className="eyebrow">Hand-picked</p>
                <h2>Featured Picks</h2>
              </div>
              <Link to="/products" className="text-link">
                Shop all <span className="arrow">→</span>
              </Link>
            </div>
          </Reveal>
          {error ? null : products === null ? (
            <LoadingGrid count={4} />
          ) : (
            <div className="product-grid">
              {featured.map((p) => (
                <ProductCard key={p.product_id} product={p} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="section container">
        <Reveal>
          <div className="assistant-feature">
            <div className="assistant-feature-copy">
              <p className="eyebrow">Personal shopping, built in</p>
              <h2>Not sure what to choose? Just ask.</h2>
              <p>
                Describe what you're after, even loosely, and our shopping assistant suggests real styles in stock, checks
                your size, and puts the matches right on the page.
              </p>
              <div className="ask-chips">
                {ASK_EXAMPLES.map((q) => (
                  <button key={q} className="ask-chip" onClick={() => openChat(q)}>
                    “{q}”
                  </button>
                ))}
              </div>
            </div>
            <div className="assistant-feature-demo" aria-hidden="true">
              <p className="demo-caption">Example conversation</p>
              <p className="demo-bubble demo-user">Something cozy for winter?</p>
              <p className="demo-bubble demo-bot">
                For something cozy, I'd go with a warm layer: a fleece jacket or a heavyweight crewneck. I've put a few on
                the page. Any color you prefer?
              </p>
              <p className="demo-bubble demo-user">Does the fleece come in gray?</p>
            </div>
          </div>
        </Reveal>
      </section>

      {family.length > 0 && (
        <section className="section section-tinted">
          <div className="container">
            <Reveal>
              <div className="section-heading">
                <div>
                  <p className="eyebrow">For proud families</p>
                  <h2>Gifts for Every Bulldog in the Family</h2>
                </div>
                <Link to={assistantViewUrl("family")} className="text-link">
                  See more <span className="arrow">→</span>
                </Link>
              </div>
            </Reveal>
            <div className="product-grid">
              {family.map((p) => (
                <ProductCard key={p.product_id} product={p} />
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="section container">
        <div className="promise-grid">
          {PROMISES.map((p, i) => (
            <Reveal key={p.title} delay={i * 70}>
              <div className="promise">
                <span className="promise-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round">
                    <path d={p.icon} />
                  </svg>
                </span>
                <p className="promise-title">{p.title}</p>
                <p className="promise-text">{p.text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="section container section-last">
        <Reveal>
          <div className="banner">
            <div>
              <p className="eyebrow">Celebrate every milestone</p>
              <h2>From move-in day to commencement.</h2>
              <p>
                A first semester, a big game, or graduation day: find something they'll wear long after the season ends.
              </p>
            </div>
            <Link to="/products" className="btn btn-cream btn-lg">
              Browse the Collection <span className="arrow">→</span>
            </Link>
          </div>
        </Reveal>
      </section>
    </>
  );
}
