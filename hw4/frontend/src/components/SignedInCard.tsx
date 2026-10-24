import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

/** Shown on the Log In and Create Account pages when the customer is already signed in. */
export default function SignedInCard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;

  return (
    <div className="auth-card auth-card-center">
      <span className="signed-in-avatar" aria-hidden="true">
        {user.first_name.charAt(0).toUpperCase()}
      </span>
      <p className="eyebrow">You're signed in</p>
      <h1>Hi, {user.first_name}!</h1>
      <p className="auth-intro">You're logged in to your Campus Customs account.</p>
      <div className="status-actions">
        <Link to="/products" className="btn btn-primary">
          Continue Shopping
        </Link>
        <button
          className="btn btn-outline"
          onClick={async () => {
            await logout();
            navigate("/login", { state: { loggedOut: true } });
          }}
        >
          Log Out
        </button>
      </div>
    </div>
  );
}
