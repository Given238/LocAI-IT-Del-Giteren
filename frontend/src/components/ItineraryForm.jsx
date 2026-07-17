import { useState } from "react";
import { INTEREST_OPTIONS } from "../constants";

const initialForm = {
  budget: "",
  durationNights: "1",
  startLocation: "",
  interests: [],
};

export default function ItineraryForm({ onSubmit, disabled }) {
  const [form, setForm] = useState(initialForm);
  const [touched, setTouched] = useState(false);

  const budgetValue = Number(form.budget);
  const durationValue = Number(form.durationNights);
  const budgetValid = form.budget !== "" && budgetValue > 0;
  const durationValid = form.durationNights !== "" && durationValue >= 0 && Number.isInteger(durationValue);
  const locationValid = form.startLocation.trim().length > 0;
  const formValid = budgetValid && durationValid && locationValid;

  function toggleInterest(key) {
    setForm((f) => ({
      ...f,
      interests: f.interests.includes(key)
        ? f.interests.filter((k) => k !== key)
        : [...f.interests, key],
    }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    setTouched(true);
    if (!formValid) return;
    onSubmit({
      budget: budgetValue,
      duration_nights: durationValue,
      start_location: form.startLocation.trim(),
      interests: form.interests.length > 0 ? form.interests : null,
    });
  }

  return (
    <form className="itinerary-form" onSubmit={handleSubmit} noValidate>
      <div className="form-row">
        <label htmlFor="budget">Budget (IDR)</label>
        <input
          id="budget"
          type="number"
          min="1"
          step="1000"
          placeholder="e.g. 500000"
          value={form.budget}
          disabled={disabled}
          onChange={(e) => setForm((f) => ({ ...f, budget: e.target.value }))}
        />
        {touched && !budgetValid && (
          <span className="field-error">Enter a budget greater than 0.</span>
        )}
      </div>

      <div className="form-row">
        <label htmlFor="duration">Duration (nights)</label>
        <input
          id="duration"
          type="number"
          min="0"
          step="1"
          value={form.durationNights}
          disabled={disabled}
          onChange={(e) => setForm((f) => ({ ...f, durationNights: e.target.value }))}
        />
        <span className="field-hint">0 = same-day trip, no overnight stay</span>
        {touched && !durationValid && (
          <span className="field-error">Enter 0 or more nights.</span>
        )}
      </div>

      <div className="form-row">
        <label htmlFor="start-location">Starting location</label>
        <input
          id="start-location"
          type="text"
          placeholder="e.g. Sibolga"
          value={form.startLocation}
          disabled={disabled}
          onChange={(e) => setForm((f) => ({ ...f, startLocation: e.target.value }))}
        />
        {touched && !locationValid && (
          <span className="field-error">Enter where you're starting from.</span>
        )}
      </div>

      <fieldset className="form-row">
        <legend>Interests (optional)</legend>
        <div className="interest-grid">
          {INTEREST_OPTIONS.map(({ key, label }) => (
            <label key={key} className="interest-checkbox">
              <input
                type="checkbox"
                checked={form.interests.includes(key)}
                disabled={disabled}
                onChange={() => toggleInterest(key)}
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      <button type="submit" className="submit-button" disabled={disabled}>
        {disabled ? "Building itinerary..." : "Build my itinerary"}
      </button>
    </form>
  );
}
