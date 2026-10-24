import { Link } from "react-router-dom";
import { CATEGORIES } from "../api";
import { openChat } from "../chatEvents";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container footer-cta">
        <div>
          <p className="footer-cta-eyebrow">Need a hand choosing?</p>
          <p className="footer-cta-title">Our shopping assistant knows every style and size we have in stock.</p>
        </div>
        <button className="btn btn-cream" onClick={() => openChat()}>
          Chat with the assistant
        </button>
      </div>
      <div className="container footer-grid">
        <div>
          <p className="footer-brand">Campus Customs</p>
          <p className="footer-text">
            Yale apparel and gifts for students, families, alumni, and everyone who bleeds Yale blue.
          </p>
        </div>
        <div>
          <p className="footer-heading">Shop</p>
          <ul className="footer-links">
            <li>
              <Link to="/products">Shop All</Link>
            </li>
            {CATEGORIES.map((c) => (
              <li key={c.slug}>
                <Link to={`/products?category=${c.slug}`}>{c.label}</Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="footer-heading">Company</p>
          <ul className="footer-links">
            <li>
              <Link to="/about">About Us</Link>
            </li>
            <li>
              <Link to="/login">Log In</Link>
            </li>
            <li>
              <Link to="/create-account">Create Account</Link>
            </li>
          </ul>
        </div>
      </div>
      <div className="container footer-bottom">
        <p>© {new Date().getFullYear()} Campus Customs. A student project for MGT 409; not affiliated with Yale University.</p>
        <p className="footer-motto">New Haven, Connecticut</p>
      </div>
    </footer>
  );
}
