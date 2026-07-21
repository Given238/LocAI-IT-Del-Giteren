import { useState } from "react";
import { INTEREST_OPTIONS, LOCALE_OPTIONS } from "../constants";
import { isValidBudget, isValidDuration, isValidStartLocation } from "../validation";

const STEPS = ["welcome", "location", "budget", "duration", "interests", "locale", "review"];

function draftFromProfile(profile) {
  return {
    startLocation: profile?.start_location ?? "",
    budget: profile?.budget != null ? String(profile.budget) : "",
    durationNights: profile?.duration_nights != null ? String(profile.duration_nights) : "",
    interests: profile?.interests ?? [],
    locale: profile?.locale ?? "",
  };
}

function draftToProfile(draft) {
  return {
    start_location: draft.startLocation.trim() || null,
    budget: isValidBudget(draft.budget) ? Number(draft.budget) : null,
    duration_nights: isValidDuration(draft.durationNights) ? Number(draft.durationNights) : null,
    interests: draft.interests.length > 0 ? draft.interests : null,
    locale: draft.locale || null,
  };
}

export default function Onboarding({ initialProfile, onFinish, onDismiss, isFirstRun }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [draft, setDraft] = useState(() => draftFromProfile(initialProfile));
  const step = STEPS[stepIndex];

  const locationOk = draft.startLocation === "" || isValidStartLocation(draft.startLocation);
  const budgetOk = draft.budget === "" || isValidBudget(draft.budget);
  const durationOk = draft.durationNights === "" || isValidDuration(draft.durationNights);

  function go(delta) {
    setStepIndex((i) => Math.max(0, Math.min(STEPS.length - 1, i + delta)));
  }

  function finishNow() {
    onFinish(draftToProfile(draft));
  }

  // First run: closing without finishing still counts as "seen it" -- saves
  // whatever was filled in so far and doesn't nag again next load. Editing
  // an existing profile later: closing is a pure cancel, discarding
  // whatever was changed in this session and keeping the saved profile as-is.
  const handleDismiss = isFirstRun ? finishNow : onDismiss;

  function toggleInterest(key) {
    setDraft((d) => ({
      ...d,
      interests: d.interests.includes(key) ? d.interests.filter((k) => k !== key) : [...d.interests, key],
    }));
  }

  const localeLabel = LOCALE_OPTIONS.find((o) => o.key === draft.locale)?.label || "Not set";

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-card">
        <button type="button" className="onboarding-dismiss" onClick={handleDismiss} aria-label="Close">
          ✕
        </button>
        <div className="onboarding-progress">
          {STEPS.map((s, i) => (
            <span key={s} className={`onboarding-dot ${i === stepIndex ? "active" : ""} ${i < stepIndex ? "done" : ""}`} />
          ))}
        </div>

        {step === "welcome" && (
          <div className="onboarding-step">
            <h2>Let's get your trip basics</h2>
            <p>
              A few quick questions -- budget, dates, where you're starting from, what you like, and
              where you're visiting from. Answer as many or as few as you want; you can always change
              them later, and you can jump straight to chat or the form right now if you'd rather.
            </p>
            <div className="onboarding-nav">
              <button type="button" className="onboarding-skip" onClick={finishNow}>
                Skip for now
              </button>
              <button type="button" className="submit-button" onClick={() => go(1)}>
                Let's go
              </button>
            </div>
          </div>
        )}

        {step === "location" && (
          <div className="onboarding-step">
            <h2>Where will you be starting your trip from?</h2>
            <input
              type="text"
              autoFocus
              placeholder="e.g. Sibolga"
              value={draft.startLocation}
              onChange={(e) => setDraft((d) => ({ ...d, startLocation: e.target.value }))}
            />
            {!locationOk && <span className="field-error">That doesn't look like a location -- try again or leave it blank.</span>}
            <div className="onboarding-nav">
              <button type="button" className="onboarding-back" onClick={() => go(-1)}>Back</button>
              <button type="button" className="onboarding-skip" onClick={() => go(1)}>Skip this question</button>
              <button type="button" className="submit-button" disabled={!locationOk} onClick={() => go(1)}>Next</button>
            </div>
          </div>
        )}

        {step === "budget" && (
          <div className="onboarding-step">
            <h2>What's your budget for this trip?</h2>
            <input
              type="number"
              autoFocus
              min="1"
              step="1000"
              placeholder="e.g. 500000 (IDR)"
              value={draft.budget}
              onChange={(e) => setDraft((d) => ({ ...d, budget: e.target.value }))}
            />
            {!budgetOk && <span className="field-error">Enter a budget greater than 0, or leave it blank.</span>}
            <div className="onboarding-nav">
              <button type="button" className="onboarding-back" onClick={() => go(-1)}>Back</button>
              <button type="button" className="onboarding-skip" onClick={() => go(1)}>Skip this question</button>
              <button type="button" className="submit-button" disabled={!budgetOk} onClick={() => go(1)}>Next</button>
            </div>
          </div>
        )}

        {step === "duration" && (
          <div className="onboarding-step">
            <h2>How many nights, typically?</h2>
            <input
              type="number"
              autoFocus
              min="0"
              step="1"
              placeholder="0 = same-day trips"
              value={draft.durationNights}
              onChange={(e) => setDraft((d) => ({ ...d, durationNights: e.target.value }))}
            />
            <span className="field-hint">0 = same-day trip, no overnight stay</span>
            {!durationOk && <span className="field-error">Enter 0 or more nights, or leave it blank.</span>}
            <div className="onboarding-nav">
              <button type="button" className="onboarding-back" onClick={() => go(-1)}>Back</button>
              <button type="button" className="onboarding-skip" onClick={() => go(1)}>Skip this question</button>
              <button type="button" className="submit-button" disabled={!durationOk} onClick={() => go(1)}>Next</button>
            </div>
          </div>
        )}

        {step === "interests" && (
          <div className="onboarding-step">
            <h2>What are you interested in?</h2>
            <div className="interest-grid">
              {INTEREST_OPTIONS.map(({ key, label }) => (
                <label key={key} className="interest-checkbox">
                  <input
                    type="checkbox"
                    checked={draft.interests.includes(key)}
                    onChange={() => toggleInterest(key)}
                  />
                  {label}
                </label>
              ))}
            </div>
            <div className="onboarding-nav">
              <button type="button" className="onboarding-back" onClick={() => go(-1)}>Back</button>
              <button type="button" className="onboarding-skip" onClick={() => go(1)}>Skip this question</button>
              <button type="button" className="submit-button" onClick={() => go(1)}>Next</button>
            </div>
          </div>
        )}

        {step === "locale" && (
          <div className="onboarding-step">
            <h2>Where are you visiting from?</h2>
            <p className="onboarding-substep-hint">
              This only affects the tone of the narrative text (and, if you use voice, which voice
              reads it) -- it never changes which places or prices you see.
            </p>
            <select
              className="locale-select"
              value={draft.locale}
              onChange={(e) => setDraft((d) => ({ ...d, locale: e.target.value }))}
            >
              {LOCALE_OPTIONS.map(({ key, label }) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
            <div className="onboarding-nav">
              <button type="button" className="onboarding-back" onClick={() => go(-1)}>Back</button>
              <button type="button" className="submit-button" onClick={() => go(1)}>Next</button>
            </div>
          </div>
        )}

        {step === "review" && (
          <div className="onboarding-step">
            <h2>Here's what we've got</h2>
            <ul className="onboarding-review">
              <li><span>Starting from</span><b>{draft.startLocation || "Not set"}</b><button type="button" onClick={() => setStepIndex(1)}>Edit</button></li>
              <li><span>Budget</span><b>{draft.budget ? `Rp${Number(draft.budget).toLocaleString("id-ID")}` : "Not set"}</b><button type="button" onClick={() => setStepIndex(2)}>Edit</button></li>
              <li><span>Duration</span><b>{draft.durationNights !== "" ? `${draft.durationNights} night(s)` : "Not set"}</b><button type="button" onClick={() => setStepIndex(3)}>Edit</button></li>
              <li><span>Interests</span><b>{draft.interests.length > 0 ? draft.interests.join(", ") : "None"}</b><button type="button" onClick={() => setStepIndex(4)}>Edit</button></li>
              <li><span>Visiting from</span><b>{localeLabel}</b><button type="button" onClick={() => setStepIndex(5)}>Edit</button></li>
            </ul>
            <p className="onboarding-substep-hint">
              This pre-fills chat, voice, and the form -- you can still change anything per-session,
              and revisit this anytime from "Edit my preferences".
            </p>
            <div className="onboarding-nav">
              <button type="button" className="onboarding-back" onClick={() => go(-1)}>Back</button>
              <button type="button" className="submit-button" onClick={finishNow}>Save &amp; start planning</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
