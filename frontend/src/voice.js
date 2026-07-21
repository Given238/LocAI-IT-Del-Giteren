// Browser Web Speech API helpers (SpeechRecognition + SpeechSynthesis).
// No backend involvement -- STT transcript is sent through the exact same
// /chat call as typed text, and TTS just reads back the reply already
// returned. Locale here is the same key used for narrative tone
// (see constants.js LOCALE_OPTIONS / backend/llm.py LOCALE_TONE_INSTRUCTIONS).
//
// Only "indonesian" narrative text is actually Bahasa Indonesia today --
// every other locale writes ENGLISH with a regional tone/register (see
// LOCALE_TONE_INSTRUCTIONS in backend/llm.py). Those five must never try a
// native-language voice, not even as a first attempt before an English
// fallback: on a machine that genuinely has e.g. a Vietnamese voice
// installed, trying it first would succeed at finding *a* voice and then
// use it to read English text, mispronouncing it -- worse than falling
// back, since it looks like it worked. The voice has to match the actual
// language of the text, not the locale's name. So: real language first
// only where the text really is that language; everywhere else, a
// regionally-flavored English voice if the browser happens to expose one
// (rare, but harmless to try), then any English voice, then the browser's
// bare default. Revisit only if narrative generation for those locales
// ever becomes genuinely native-language.
export const LOCALE_VOICE_LANG = {
  "": [],
  indonesian: ["id-ID", "id"],
  malaysian: ["en-MY", "en"],
  singaporean: ["en-SG", "en"],
  filipino: ["en-PH", "en"],
  thai: ["en-TH", "en"],
  vietnamese: ["en-VN", "en"],
};

// Separate on purpose: LOCALE_VOICE_LANG governs what language the bot's
// TEXT is written in (English for everything but Indonesian, so TTS must
// speak English regardless of locale). Speech RECOGNITION is the opposite
// concern -- what language the user is likely speaking to the mic, which
// is their own regional language regardless of what language the bot
// replies in. Reusing LOCALE_VOICE_LANG for recognition.lang was a real
// bug: a Filipino-locale user speaking Tagalog got recognition.lang
// "en-PH" (English), so the recognizer tried to parse Tagalog audio as
// English and produced garbled transcripts -- found via real Filipino
// speech input during testing, not something a mocked test would catch.
export const LOCALE_RECOGNITION_LANG = {
  "": [],
  indonesian: ["id-ID", "id"],
  malaysian: ["ms-MY", "ms", "en-MY", "en"],
  singaporean: ["en-SG", "en"],
  filipino: ["fil-PH", "tl-PH", "en-PH", "en"],
  thai: ["th-TH", "th", "en-TH", "en"],
  vietnamese: ["vi-VN", "vi", "en-VN", "en"],
};

export function isSpeechRecognitionSupported() {
  return typeof window !== "undefined" && Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
}

export function isSpeechSynthesisSupported() {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

let cachedVoicesPromise = null;

function loadVoices() {
  if (!isSpeechSynthesisSupported()) return Promise.resolve([]);
  if (cachedVoicesPromise) return cachedVoicesPromise;

  const promise = new Promise((resolve) => {
    const existing = window.speechSynthesis.getVoices();
    if (existing.length > 0) {
      resolve(existing);
      return;
    }
    const handle = () => {
      const voices = window.speechSynthesis.getVoices();
      window.speechSynthesis.removeEventListener("voiceschanged", handle);
      resolve(voices);
    };
    window.speechSynthesis.addEventListener("voiceschanged", handle);
    // Some engines populate voices synchronously without ever firing
    // voiceschanged again after the initial (empty) read -- don't hang.
    setTimeout(() => {
      window.speechSynthesis.removeEventListener("voiceschanged", handle);
      resolve(window.speechSynthesis.getVoices());
    }, 1000);
  }).then((voices) => {
    // Don't permanently memoize a *timing* failure -- if this resolved
    // empty because voices genuinely hadn't finished loading yet inside
    // the 1s window, the next caller should get a chance to see them
    // rather than being stuck treating every locale as unavailable for
    // the rest of the session.
    if (voices.length === 0) cachedVoicesPromise = null;
    return voices;
  });

  cachedVoicesPromise = promise;
  return promise;
}

// Exported for tests that need to force a specific voice list rather than
// whatever happens to be installed on the machine running the browser.
export function _resetVoiceCache() {
  cachedVoicesPromise = null;
}

export async function pickVoiceForLocale(localeKey) {
  const voices = await loadVoices();
  const candidates = LOCALE_VOICE_LANG[localeKey || ""] || [];
  for (const tag of candidates) {
    const exact = voices.find((v) => v.lang.toLowerCase() === tag.toLowerCase());
    if (exact) return { voice: exact, requestedTag: tag };
    const prefixed = voices.find((v) => v.lang.toLowerCase().startsWith(tag.toLowerCase().split("-")[0]));
    if (prefixed) return { voice: prefixed, requestedTag: tag };
  }
  return { voice: null, requestedTag: candidates[0] || null };
}

// Speaks `text` using the voice mapped from `localeKey`, falling back to
// the browser's default voice (never failing silently/erroring) when no
// matching voice is installed. Always logs requested vs. actually-used so
// a fallback is visible during testing/demo, not just silently accepted.
//
// `onVoiceSelected` fires as soon as the voice decision is made -- that
// decision is already final at that point, so UI that just wants to show
// "which voice is this" shouldn't wait any longer than that. `onEnd` is a
// separate, best-effort "finished/failed speaking" signal for anything
// that genuinely needs playback completion; found during testing that
// speak() calls issued after an async gap (e.g. following a network
// response, as opposed to a direct synchronous user-gesture handler)
// don't reliably fire onend/onerror in every environment, so nothing
// user-visible should depend on onEnd alone ever firing.
export async function speak(text, localeKey, { onVoiceSelected, onEnd } = {}) {
  if (!isSpeechSynthesisSupported() || !text) {
    const result = { requestedTag: null, usedVoice: null, fellBack: false, supported: false };
    if (onVoiceSelected) onVoiceSelected(result);
    if (onEnd) onEnd(result);
    return;
  }

  const { voice, requestedTag } = await pickVoiceForLocale(localeKey);
  const utterance = new SpeechSynthesisUtterance(text);
  if (voice) utterance.voice = voice;

  const usedLabel = voice ? `${voice.name} (${voice.lang})` : "browser default";
  const requestedLabel = requestedTag || "none (neutral locale)";
  const fellBack = Boolean(requestedTag) && !voice;
  console.log(
    `[voice] locale="${localeKey || "(neutral)"}" requested~"${requestedLabel}" -> using "${usedLabel}"` +
      (fellBack ? " (FALLBACK: no matching voice installed)" : ""),
  );

  const result = {
    requestedTag,
    usedVoice: voice ? { name: voice.name, lang: voice.lang } : null,
    fellBack,
    supported: true,
  };
  if (onVoiceSelected) onVoiceSelected(result);
  utterance.onend = () => { if (onEnd) onEnd(result); };
  utterance.onerror = () => { if (onEnd) onEnd(result); };

  window.speechSynthesis.cancel(); // don't let replies queue/overlap
  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking() {
  if (isSpeechSynthesisSupported()) window.speechSynthesis.cancel();
}

// Returns a configured SpeechRecognition instance (not yet started), or
// null if the browser doesn't support it. Single-utterance, final-result
// only -- kept simple since the transcript just becomes one chat message.
export function createRecognizer(localeKey, { onResult, onError, onEnd } = {}) {
  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognitionCtor) return null;

  const recognition = new SpeechRecognitionCtor();
  const candidates = LOCALE_RECOGNITION_LANG[localeKey || ""] || [];
  recognition.lang = candidates[0] || navigator.language || "en-US";
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    if (onResult) onResult(transcript);
  };
  recognition.onerror = (event) => {
    if (onError) onError(event.error);
  };
  recognition.onend = () => {
    if (onEnd) onEnd();
  };

  return recognition;
}
