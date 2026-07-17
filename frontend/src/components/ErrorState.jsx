export default function ErrorState({ title, message, variant = "error" }) {
  return (
    <div className={`status-panel error-panel ${variant}`} role="alert">
      <p className="error-title">{title}</p>
      {message && <p className="status-subtext">{message}</p>}
    </div>
  );
}
