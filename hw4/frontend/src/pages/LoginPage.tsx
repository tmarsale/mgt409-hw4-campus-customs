import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../api";
import { useAuth } from "../auth";
import SignedInCard from "../components/SignedInCard";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const { user, checking, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const loggedOut = Boolean((location.state as { loggedOut?: boolean } | null)?.loggedOut);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const next: typeof errors = {};
    if (!EMAIL.test(email.trim())) next.email = "Enter a valid email address.";
    if (!password) next.password = "Enter your password.";
    setErrors(next);
    setFormError(null);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate("/", { state: { welcome: true } });
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "We couldn't reach the store. Please try again.");
      setPassword(""); // never keep a rejected password around
    } finally {
      setSubmitting(false);
    }
  }

  if (!checking && user) {
    return (
      <div className="container page auth-page">
        <SignedInCard />
      </div>
    );
  }

  return (
    <div className="container page auth-page">
      <div className="auth-card">
        <p className="eyebrow">Welcome back</p>
        <h1>Log In</h1>
        <p className="auth-intro">Sign in to your Campus Customs account.</p>

        {loggedOut && !formError && (
          <p className="form-notice" role="status">
            You've been logged out. See you soon!
          </p>
        )}
        {formError && (
          <p className="form-alert" role="alert">
            {formError}
          </p>
        )}

        <form onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="login-email">Email address</label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={Boolean(errors.email)}
              aria-describedby={errors.email ? "login-email-error" : undefined}
            />
            {errors.email && <p id="login-email-error" className="field-error">{errors.email}</p>}
          </div>

          <div className="field">
            <div className="field-label-row">
              <label htmlFor="login-password">Password</label>
              <button type="button" className="link-button" onClick={() => setShowPassword((s) => !s)}>
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            <input
              id="login-password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={Boolean(errors.password)}
              aria-describedby={errors.password ? "login-password-error" : undefined}
            />
            {errors.password && <p id="login-password-error" className="field-error">{errors.password}</p>}
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? "Logging in…" : "Log In"}
          </button>
        </form>

        <p className="auth-switch">
          New to Campus Customs? <Link to="/create-account">Create an account</Link>
        </p>
      </div>
    </div>
  );
}
