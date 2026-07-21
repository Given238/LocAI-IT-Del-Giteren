import { useEffect, useRef, useState } from "react";
import { fetchChat, ApiError } from "../api";
import { LOCALE_OPTIONS } from "../constants";
import {
  createRecognizer,
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported,
  speak,
  stopSpeaking,
} from "../voice";
import ResultsView from "./ResultsView";

function toHistory(messages) {
  return messages.map(({ role, content, itinerary }) => ({
    role,
    content,
    ...(itinerary ? { itinerary } : {}),
  }));
}

const sttSupported = isSpeechRecognitionSupported();
const ttsSupported = isSpeechSynthesisSupported();

// Plain, unformatted numbers on purpose -- this text is parsed by the chat
// LLM, not read by a human. Using "Rp500.000" (id-ID's period-as-thousands-
// separator) here caused a real bug: the LLM read "500.000" as an unclear
// number and asked a clarifying question instead of calling the tool, even
// though the value was right there. Nicely-formatted "Rp500.000" is fine
// for the button's own visible label (a human reads that), just not for
// the message actually sent.
function quickStartText(profile) {
  const parts = [`a budget of Rp${profile.budget}`, `${profile.duration_nights} night(s)`, `starting from ${profile.start_location}`];
  let text = `Plan a trip with ${parts.join(", ")}`;
  if (profile.interests?.length) text += `, interested in ${profile.interests.join(", ")}`;
  return text + ".";
}

export default function ChatView({ locale, onLocaleChange, profile }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [voiceMode, setVoiceMode] = useState(false);
  const [recording, setRecording] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("");
  const messagesRef = useRef(null);
  const recognizerRef = useRef(null);
  const localeRef = useRef(locale);
  localeRef.current = locale;
  // speak() calls are fire-and-forget; if a reply arrives while the
  // previous one is still "finishing" (cancel() doesn't fire onend
  // synchronously), a stale onEnd could overwrite the status line with an
  // older result. Only the most recent call is allowed to update it.
  const speechSeqRef = useRef(0);

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, sending]);

  // Stop any in-progress recognition/speech if the component unmounts, and
  // if voice mode gets switched off mid-speech.
  useEffect(() => {
    if (!voiceMode) stopSpeaking();
  }, [voiceMode]);
  useEffect(() => () => { recognizerRef.current?.abort(); stopSpeaking(); }, []);

  async function sendMessage(text) {
    if (!text || sending) return;

    const historyForApi = toHistory(messages);
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setError("");
    setSending(true);

    try {
      const body = await fetchChat(historyForApi, text);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: body.reply,
          itinerary: body.itinerary || null,
          pdfBase64: body.pdf_base64 || null,
          pdfFilename: body.pdf_filename || null,
        },
      ]);
      if (voiceMode && body.reply) {
        const seq = ++speechSeqRef.current;
        speak(body.reply, localeRef.current, {
          onVoiceSelected: ({ supported, usedVoice, fellBack }) => {
            if (!supported || seq !== speechSeqRef.current) return;
            setVoiceStatus(
              fellBack
                ? `Voice: ${usedVoice ? usedVoice.name : "browser default"} (no voice installed for this locale -- fell back)`
                : `Voice: ${usedVoice ? `${usedVoice.name} (${usedVoice.lang})` : "browser default"}`,
            );
          },
        });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSending(false);
    }
  }

  function handleTextSubmit(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    sendMessage(text);
  }

  function toggleRecording() {
    if (recording) {
      recognizerRef.current?.stop();
      return;
    }

    // Mic permission is requested here, by the browser, only now -- never
    // on page load or just from switching voice mode on.
    const recognizer = createRecognizer(locale, {
      onResult: (transcript) => {
        setRecording(false);
        sendMessage(transcript.trim());
      },
      onError: (err) => {
        setRecording(false);
        if (err !== "no-speech" && err !== "aborted") {
          setError(`Voice input error: ${err}`);
        }
      },
      onEnd: () => setRecording(false),
    });

    if (!recognizer) {
      setError("Voice input isn't supported in this browser.");
      return;
    }
    recognizerRef.current = recognizer;
    setError("");
    setRecording(true);
    recognizer.start();
  }

  return (
    <div className="chat-view">
      <div className="chat-intro">
        Tell me your budget, trip length, and where you're starting from, and I'll build a real,
        verified Danau Toba itinerary -- the same grounded pipeline as the form, just conversational.
      </div>

      <div className="chat-toolbar">
        <label className="chat-locale-label">
          Locale
          <select
            className="locale-select chat-locale-select"
            value={locale}
            onChange={(e) => onLocaleChange(e.target.value)}
          >
            {LOCALE_OPTIONS.map(({ key, label }) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>

        {(sttSupported || ttsSupported) && (
          <label className="voice-mode-toggle">
            <input
              type="checkbox"
              checked={voiceMode}
              onChange={(e) => setVoiceMode(e.target.checked)}
            />
            Voice mode
          </label>
        )}
        {!sttSupported && !ttsSupported && (
          <span className="field-hint">Voice isn't supported in this browser.</span>
        )}
      </div>

      {messages.length === 0 && profile?.budget != null && profile?.duration_nights != null && profile?.start_location && (
        <button type="button" className="quick-start-chip" onClick={() => sendMessage(quickStartText(profile))}>
          Use my saved trip: Rp{Number(profile.budget).toLocaleString("id-ID")} &middot; {profile.duration_nights} night(s) &middot; from {profile.start_location} →
        </button>
      )}

      <div className="chat-messages" ref={messagesRef}>
        {messages.map((m, i) => {
          const showResults = m.role === "assistant" && m.itinerary && m.itinerary.feasible && !m.pdfBase64;
          return (
            <div key={i} className={`chat-bubble-row ${m.role}`}>
              <div className="chat-bubble">
                {!showResults && <p className="chat-bubble-text">{m.content}</p>}
                {m.pdfBase64 && (
                  <a
                    className="chat-pdf-link"
                    href={`data:application/pdf;base64,${m.pdfBase64}`}
                    download={m.pdfFilename || "locai-itinerary.pdf"}
                  >
                    Download {m.pdfFilename || "itinerary.pdf"}
                  </a>
                )}
                {showResults && <ResultsView result={m.itinerary} collapsibleMap />}
              </div>
            </div>
          );
        })}

        {sending && (
          <div className="chat-bubble-row assistant">
            <div className="chat-bubble chat-bubble-typing">Thinking&hellip;</div>
          </div>
        )}
      </div>

      {error && <p className="chat-error">{error}</p>}
      {voiceMode && voiceStatus && <p className="voice-status">{voiceStatus}</p>}

      <form className="chat-input-row" onSubmit={handleTextSubmit}>
        {voiceMode && sttSupported && (
          <button
            type="button"
            className={`mic-button ${recording ? "recording" : ""}`}
            onClick={toggleRecording}
            aria-pressed={recording}
            title={recording ? "Stop recording" : "Speak your message"}
          >
            {recording ? "● Listening..." : "🎤"}
          </button>
        )}
        <input
          type="text"
          placeholder="e.g. I want to visit Toba, budget 500000, from Sibolga, 1 night"
          value={input}
          disabled={sending}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" className="submit-button" disabled={sending || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
