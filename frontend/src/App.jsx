import { useEffect, useState } from "react";
import { fetchItinerary } from "./api";
import { getMe, logout as apiLogout, saveProfileRemote } from "./auth";
import ItineraryForm from "./components/ItineraryForm";
import LoadingState from "./components/LoadingState";
import ErrorState from "./components/ErrorState";
import ResultsView from "./components/ResultsView";
import ChatView from "./components/ChatView";
import Onboarding from "./components/Onboarding";
import AuthPanel from "./components/AuthPanel";
import { loadProfile, saveProfile, hasOnboarded } from "./profile";
import "./App.css";

function localProfileHasData(local) {
  return Boolean(
    local && (local.budget != null || local.start_location || local.duration_nights != null
      || local.locale || (local.interests && local.interests.length > 0)),
  );
}

export default function App() {
  const [mode, setMode] = useState("chat"); // chat | form
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [profile, setProfile] = useState(() => loadProfile());
  const [profileVersion, setProfileVersion] = useState(0);
  const [showOnboarding, setShowOnboarding] = useState(() => !hasOnboarded(loadProfile()));
  // Separate from hasOnboarded(profile) on purpose -- that check only means
  // something for the localStorage guest shape (its "onboarded" flag).
  // Backend profiles have no such flag; "first run" here just means
  // "onboarding is showing itself automatically because there's nothing
  // saved yet," as opposed to the user explicitly clicking Edit preferences
  // on an existing profile. Determines whether the overlay's X button
  // behaves like Skip (save-and-close) or Cancel (discard-and-close).
  const [onboardingIsFirstRun, setOnboardingIsFirstRun] = useState(() => !hasOnboarded(loadProfile()));
  const [showAuthPanel, setShowAuthPanel] = useState(false);
  const [authUser, setAuthUser] = useState(null);
  // Single source of truth for locale -- read by the form's narrative-tone
  // dropdown AND by chat's voice output. Reads the stored profile FIRST
  // (per "Locale: single source of truth" in CLAUDE.md); the dropdown
  // remains a live per-session override on top of that -- changing it here
  // does NOT write back to the stored profile, only completing/editing
  // onboarding does.
  const [locale, setLocale] = useState(() => loadProfile()?.locale || "");

  // Applies a resolved (user, profile) pair from the backend -- shared by
  // the initial session check and by AuthPanel's onAuthed callback so both
  // paths do the exact same "migrate local profile if the account has none
  // yet" thing, not two slightly different copies of it.
  async function applyAuthState(user, remoteProfile) {
    setAuthUser(user);
    if (remoteProfile) {
      setProfile(remoteProfile);
      setLocale(remoteProfile.locale || "");
      setShowOnboarding(false);
    } else {
      const local = loadProfile();
      if (localProfileHasData(local)) {
        const migrated = await saveProfileRemote(local);
        setProfile(migrated);
        setLocale(migrated.locale || "");
        setShowOnboarding(false);
      } else {
        setOnboardingIsFirstRun(true);
        setShowOnboarding(true);
      }
    }
    setProfileVersion((v) => v + 1);
  }

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((data) => {
        if (cancelled || !data?.user) return;
        applyAuthState(data.user, data.profile);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleAuthed(user) {
    const me = await getMe();
    await applyAuthState(user, me?.profile);
    setShowAuthPanel(false);
  }

  async function handleLogout() {
    await apiLogout().catch(() => {});
    setAuthUser(null);
    const local = loadProfile();
    setProfile(local);
    setLocale(local?.locale || "");
    setProfileVersion((v) => v + 1);
  }

  async function handleOnboardingFinish(collected) {
    if (authUser) {
      const saved = await saveProfileRemote(collected);
      setProfile(saved);
      setLocale(saved.locale || "");
    } else {
      saveProfile(collected);
      setProfile(loadProfile());
      setLocale(collected.locale || "");
    }
    setProfileVersion((v) => v + 1);
    setShowOnboarding(false);
  }

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
        <div className="mode-toggle" role="tablist" aria-label="Planning mode">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "chat"}
            className={`mode-tab ${mode === "chat" ? "active" : ""}`}
            onClick={() => setMode("chat")}
          >
            Chat
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "form"}
            className={`mode-tab ${mode === "form" ? "active" : ""}`}
            onClick={() => setMode("form")}
          >
            Form
          </button>
        </div>
        <button
          type="button"
          className="edit-preferences-button"
          onClick={() => {
            setOnboardingIsFirstRun(false);
            setShowOnboarding(true);
          }}
        >
          ⚙ Edit my preferences
        </button>

        {authUser ? (
          <span className="auth-status">
            {authUser.display_name || authUser.email}
            <button type="button" className="edit-preferences-button" onClick={handleLogout}>
              Log out
            </button>
          </span>
        ) : (
          <button type="button" className="edit-preferences-button" onClick={() => setShowAuthPanel(true)}>
            Log in / Sign up
          </button>
        )}
      </header>

      {showOnboarding && (
        <Onboarding
          initialProfile={profile}
          isFirstRun={onboardingIsFirstRun}
          onFinish={handleOnboardingFinish}
          onDismiss={() => setShowOnboarding(false)}
        />
      )}

      {showAuthPanel && (
        <AuthPanel onAuthed={handleAuthed} onDismiss={() => setShowAuthPanel(false)} />
      )}

      {/*
        Both panels stay mounted at all times and are only hidden via CSS.
        Conditionally rendering (unmounting) ChatView on tab switch was
        tried first and discarded -- it reset the whole conversation any
        time someone glanced at the Form tab and came back.
      */}
      <main className={`app-main app-main-chat ${mode === "chat" ? "" : "mode-hidden"}`}>
        <ChatView locale={locale} onLocaleChange={setLocale} profile={profile} />
      </main>

      <main className={`app-main ${mode === "form" ? "" : "mode-hidden"}`}>
        <ItineraryForm
          key={profileVersion}
          onSubmit={handleSubmit}
          disabled={status === "loading"}
          locale={locale}
          onLocaleChange={setLocale}
          initialValues={profile}
        />

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
