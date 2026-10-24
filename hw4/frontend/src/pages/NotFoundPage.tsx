import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="container page">
      <div className="status-box">
        <p className="status-title">Page not found</p>
        <p>We couldn't find that page. Let's get you back to the good stuff.</p>
        <div className="status-actions">
          <Link to="/" className="btn btn-primary">
            Back to Home
          </Link>
          <Link to="/products" className="btn btn-outline">
            Shop All
          </Link>
        </div>
      </div>
    </div>
  );
}
