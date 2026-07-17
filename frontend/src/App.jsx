import { useState } from "react";
import { fetchItinerary } from "./api";
import ItineraryForm from "./components/ItineraryForm";
import LoadingState from "./components/LoadingState";
import ErrorState from "./components/ErrorState";
import ResultsView from "./components/ResultsView";
import "./App.css";

export default function App() {
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(payload) {
    setStatus("loading");
    setResult(null);
    setErrorMessage("");
    try {
      const data = await fetchItinerary(payload);
      setResult(data);
      setStatus("success");
    } catch (err) {
      setErrorMessage(err.message || "Something went wrong.");
      setStatus("error");
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>LocAI</h1>
        <p>Plan a real, budget-aware Danau Toba itinerary from the actual tourism dataset.</p>
      </header>

      <main className="app-main">
        <ItineraryForm onSubmit={handleSubmit} disabled={status === "loading"} />

        <div className="app-results">
          {status === "loading" && <LoadingState />}

          {status === "error" && (
            <ErrorState title="Couldn't build your itinerary" message={errorMessage} />
          )}

          {status === "success" && result && !result.feasible && (
            <ErrorState
              variant="infeasible"
              title="No itinerary fits those constraints"
              message={result.message}
            />
          )}

          {status === "success" && result && result.feasible && (
            <ResultsView result={result} />
          )}
        </div>
      </main>
    </div>
  );
}
