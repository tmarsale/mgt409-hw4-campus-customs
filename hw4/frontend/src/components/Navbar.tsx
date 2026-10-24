import { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/products", label: "Shop All", end: false },
  { to: "/about", label: "About Us", end: false },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { pathname } = useLocation();
  const { user, checking, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { state: { loggedOut: true } });
  }

  // A soft shadow under the header once the page scrolls, so it reads as a separate layer.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Close the mobile menu whenever the page changes.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <header className={`site-header ${scrolled ? "is-scrolled" : ""}`}>
      <div className="promo-bar">
        <span>Yale apparel &amp; gifts from New Haven</span>
        <span className="promo-dot" aria-hidden="true">✦</span>
        <span>Live stock for every size, XS–XXL</span>
        <span className="promo-dot promo-extra" aria-hidden="true">✦</span>
        <span className="promo-extra">Ask our shopping assistant anytime</span>
      </div>
      <nav className="navbar" aria-label="Main">
        <div className="container navbar-inner">
          <Link to="/" className="brand" aria-label="Campus Customs home">
            <span className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 40 46" width="34" height="40">
                <path d="M20 1.5 37.5 7v15.2c0 10.6-7.3 18.6-17.5 22.3C9.8 40.8 2.5 32.8 2.5 22.2V7z" fill="currentColor" />
                <path d="M20 5 34 9.4v12.8c0 8.7-5.8 15.4-14 18.7-8.2-3.3-14-10-14-18.7V9.4z" fill="none" stroke="#e9dfc8" strokeWidth="1" opacity=".55" />
                <text x="20" y="27.5" textAnchor="middle" fontFamily="Cormorant Garamond, Georgia, serif" fontWeight="700" fontSize="15" fill="#f6f1e7">
                  CC
                </text>
              </svg>
            </span>
            <span className="brand-text">
              <span className="brand-name">Campus Customs</span>
              <span className="brand-tagline">Yale Apparel &amp; Gifts</span>
            </span>
          </Link>

          <button
            className="menu-toggle"
            aria-expanded={open}
            aria-controls="main-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((o) => !o)}
          >
            <span className={`hamburger ${open ? "is-open" : ""}`} aria-hidden="true" />
          </button>

          <div id="main-menu" className={`nav-menu ${open ? "is-open" : ""}`}>
            <ul className="nav-links">
              {LINKS.map((link) => (
                <li key={link.to}>
                  <NavLink to={link.to} end={link.end} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                    {link.label}
                  </NavLink>
                </li>
              ))}
            </ul>
            <div className="nav-actions">
              {checking ? null : user ? (
                <>
                  <span className="nav-greeting" aria-live="polite">
                    <span className="nav-avatar" aria-hidden="true">
                      {user.first_name.charAt(0).toUpperCase()}
                    </span>
                    Hi, {user.first_name}
                  </span>
                  <button className="btn btn-outline btn-sm" onClick={handleLogout}>
                    Log Out
                  </button>
                </>
              ) : (
                <>
                  <NavLink to="/login" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                    Log In
                  </NavLink>
                  <Link to="/create-account" className="btn btn-primary btn-sm">
                    Create Account
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>
    </header>
  );
}
