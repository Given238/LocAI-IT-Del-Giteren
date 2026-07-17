export default function LoadingState() {
  return (
    <div className="status-panel loading-panel" role="status">
      <div className="spinner" aria-hidden="true" />
      <p>Building your itinerary&hellip;</p>
      <p className="status-subtext">
        This calls a live LLM and can take up to several seconds, especially for longer trips.
      </p>
    </div>
  );
}
