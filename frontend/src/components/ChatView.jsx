import { useEffect, useRef, useState } from "react";
import { fetchChat, ApiError } from "../api";
import ResultsView from "./ResultsView";

function toHistory(messages) {
  return messages.map(({ role, content, itinerary }) => ({
    role,
    content,
    ...(itinerary ? { itinerary } : {}),
  }));
}

export default function ChatView() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef(null);

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, sending]);

  async function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
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
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="chat-view">
      <div className="chat-intro">
        Tell me your budget, trip length, and where you're starting from, and I'll build a real,
        verified Danau Toba itinerary -- the same grounded pipeline as the form, just conversational.
      </div>

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

      <form className="chat-input-row" onSubmit={handleSend}>
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
