import { useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api";
import { useAuth } from "../auth";
import SignedInCard from "../components/SignedInCard";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const NAME = /^\p{L}[\p{L} '\-.]*$/u; // same rule as the backend: letters, spaces, hyphens, apostrophes
const MIN_PASSWORD = 8;
const MAX_PASSWORD = 128;

type Field = "firstName" | "lastName" | "email" | "password" | "confirm";

// Backend field names (the `users` table columns) mapped to this form's fields.
const SERVER_FIELDS: Record<string, Field> = {
  first_name: "firstName",
  last_name: "lastName",
  email: "email",
  password: "password",
  confirm_password: "confirm",
};

export default function RegisterPage() {
  const { user, checking, register } = useAuth();
  const navigate = useNavigate();
  const [values, setValues] = useState<Record<Field, string>>({ firstName: "", lastName: "", email: "", password: "", confirm: "" });
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const [formError, setFormError] = useState<{ text: string; duplicate: boolean } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const set = (field: Field) => (e: ChangeEvent<HTMLInputElement>) => setValues((v) => ({ ...v, [field]: e.target.value }));

  function validate(): Partial<Record<Field, string>> {
    const next: Partial<Record<Field, string>> = {};
    const nameError = (v: string, label: string) =>
      !v.trim() ? `Enter your ${label}.` : !NAME.test(v.trim()) || v.trim().length > 50 ? "Use letters only (spaces, hyphens, and apostrophes are fine)." : undefined;
    next.firstName = nameError(values.firstName, "first name");
    next.lastName = nameError(values.lastName, "last name");
    if (!EMAIL.test(values.email.trim())) next.email = "Enter a valid email address.";
    if (values.password.length < MIN_PASSWORD || !values.password.trim()) next.password = `Use at least ${MIN_PASSWORD} characters.`;
    else if (values.password.length > MAX_PASSWORD) next.password = `Use at most ${MAX_PASSWORD} characters.`;
    if (values.confirm !== values.password) next.confirm = "Passwords don't match.";
    return Object.fromEntries(Object.entries(next).filter(([, v]) => v)) as Partial<Record<Field, string>>;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const next = validate();
    setErrors(next);
    setFormError(null);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    try {
      await register({
        first_name: values.firstName.trim(),
        last_name: values.lastName.trim(),
        email: values.email.trim(),
        password: values.password,
        confirm_password: values.confirm,
      });
      navigate("/", { state: { welcome: true } });
    } catch (err) {
      if (err instanceof ApiError) {
        const fieldErrors: Partial<Record<Field, string>> = {};
        for (const [name, msg] of Object.entries(err.fields)) if (SERVER_FIELDS[name]) fieldErrors[SERVER_FIELDS[name]] = msg;
        setErrors(fieldErrors);
        setFormError({ text: err.message, duplicate: err.status === 409 });
      } else {
        setFormError({ text: "We couldn't reach the store. Please try again.", duplicate: false });
      }
      setValues((v) => ({ ...v, password: "", confirm: "" })); // don't keep passwords after a failed attempt
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

  const field = (id: Field, label: string, type: string, autoComplete: string, hint?: string) => (
    <div className="field">
      <label htmlFor={`reg-${id}`}>{label}</label>
      <input
        id={`reg-${id}`}
        type={type}
        autoComplete={autoComplete}
        value={values[id]}
        onChange={set(id)}
        aria-invalid={Boolean(errors[id])}
        aria-describedby={errors[id] ? `reg-${id}-error` : hint ? `reg-${id}-hint` : undefined}
      />
      {errors[id] ? (
        <p id={`reg-${id}-error`} className="field-error">{errors[id]}</p>
      ) : (
        hint && <p id={`reg-${id}-hint`} className="field-hint">{hint}</p>
      )}
    </div>
  );

  return (
    <div className="container page auth-page">
      <div className="auth-card">
        <p className="eyebrow">Join Campus Customs</p>
        <h1>Create Account</h1>
        <p className="auth-intro">Create an account to save your details and get help from our shopping assistant.</p>

        {formError && (
          <p className="form-alert" role="alert">
            {formError.text}
            {formError.duplicate && (
              <>
                {" "}
                <Link to="/login">Log in instead</Link>
              </>
            )}
          </p>
        )}

        <form onSubmit={submit} noValidate>
          <div className="field-row">
            {field("firstName", "First name", "text", "given-name")}
            {field("lastName", "Last name", "text", "family-name")}
          </div>
          {field("email", "Email address", "email", "email")}
          {field("password", "Password", "password", "new-password", `At least ${MIN_PASSWORD} characters.`)}
          {field("confirm", "Confirm password", "password", "new-password")}

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? "Creating your account…" : "Create Account"}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
