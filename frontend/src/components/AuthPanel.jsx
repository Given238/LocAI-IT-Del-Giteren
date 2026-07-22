import { useEffect, useState } from "react";
import { ApiError, googleLoginUrl, isGoogleLoginAvailable, login, signup } from "../auth";

export default function AuthPanel({ onAuthed, onDismiss }) {
  const [mode, setMode] = useState("login"); // login | signup
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [googleAvailable, setGoogleAvailable] = useState(false);

  useEffect(() => {
    isGoogleLoginAvailable().then(setGoogleAvailable);
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const user = mode === "signup"
        ? await signup(email, password, displayName)
        : await login(email, password);
      onAuthed(user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-card auth-card">
        <button type="button" className="onboarding-dismiss" onClick={onDismiss} aria-label="Close">
          ✕
        </button>

        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${mode === "login" ? "active" : ""}`}
            onClick={() => { setMode("login"); setError(""); }}
          >
            Log in
          </button>
          <button
            type="button"
            className={`auth-tab ${mode === "signup" ? "active" : ""}`}
            onClick={() => { setMode("signup"); setError(""); }}
          >
            Sign up
          </button>
        </div>

        <form className="onboarding-step" onSubmit={handleSubmit}>
          {mode === "signup" && (
            <input
              type="text"
              placeholder="Name (optional)"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          )}
          <input
            type="email"
            placeholder="Email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password"
            placeholder={mode === "signup" ? "Password (min. 8 characters)" : "Password"}
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
            required
            minLength={mode === "signup" ? 8 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && <span className="field-error">{error}</span>}

          <button type="submit" className="submit-button" disabled={submitting}>
            {submitting ? "Please wait..." : mode === "signup" ? "Create account" : "Log in"}
          </button>

          {googleAvailable && (
            <>
              <div className="auth-divider">or</div>
              <a className="google-login-button" href={googleLoginUrl()}>
                Continue with Google
              </a>
            </>
          )}

          <button type="button" className="onboarding-skip auth-guest-link" onClick={onDismiss}>
            Continue as guest instead
          </button>
        </form>
      </div>
    </div>
  );
}
