// ── Subtitle / CC component ──────────────────────────────────────────────────
// Transcript deltas arrive faster than audio plays, so text is buffered and
// dripped out at speech pace so the display stays in sync with the audio.
//
// Tunable:
const CC_WORDS = 4; // words shown per reveal tick
const CC_TICK_MS = 1400; // ms between reveals

let ccEnabled = false;
let ccQueue = ""; // incoming text not yet revealed
let ccDisplayed = ""; // text currently on screen
let ccRevealIv = null;
let ccDoneTimer = null;
let ccTranscriptDone = false; // true once the full transcript has arrived

const ccBtn = document.getElementById("ccBtn");
const ccIcon = document.getElementById("ccIcon");
const subtitleArea = document.getElementById("subtitleArea");
const subtitleClip = document.getElementById("subtitleClip");
const subtitleText = document.getElementById("subtitleText");

ccBtn.addEventListener("click", () => {
  ccEnabled = !ccEnabled;
  ccIcon.src = ccEnabled
    ? "/static/subtitle-on.svg"
    : "/static/subtitle-off.svg";
  if (!ccEnabled) clearSubtitle();
});

function _updateSubtitleDOM() {
  subtitleText.textContent = ccDisplayed;
  subtitleArea.classList.add("visible");
  requestAnimationFrame(() => {
    const overflow = subtitleText.scrollHeight - subtitleClip.clientHeight;
    subtitleText.style.transform =
      overflow > 0 ? `translateY(-${overflow}px)` : "";
  });
}

function _revealChunk() {
  if (!ccQueue.trim()) {
    // Queue is empty — stop the interval
    clearInterval(ccRevealIv);
    ccRevealIv = null;
    // If transcript is fully done, schedule the clear
    if (ccTranscriptDone) {
      ccDoneTimer = setTimeout(clearSubtitle, 4500);
      ccTranscriptDone = false;
    }
    return;
  }
  const words = ccQueue.trimStart().split(/\s+/);
  const take = Math.min(CC_WORDS, words.length);
  ccDisplayed += (ccDisplayed ? " " : "") + words.slice(0, take).join(" ");
  ccQueue = words.slice(take).join(" ");
  _updateSubtitleDOM();
}

// Called on each response.output_audio_transcript.delta
function appendSubtitle(delta) {
  if (!ccEnabled) return;
  clearTimeout(ccDoneTimer);
  ccQueue += delta;

  // Don't start the interval until a full chunk is buffered — avoids the
  // jarring "one word then a bunch" pattern on the very first reveal.
  if (!ccRevealIv) {
    const wordCount = ccQueue.trim().split(/\s+/).length;
    if (wordCount >= CC_WORDS) {
      _revealChunk();
      ccRevealIv = setInterval(_revealChunk, CC_TICK_MS);
    }
  }
}

// Called when response.output_audio_transcript.done fires.
// Does NOT dump remaining text — the interval keeps draining at pace.
function onSubtitleDone() {
  ccTranscriptDone = true;

  if (!ccRevealIv) {
    // Interval wasn't running (short response, < CC_WORDS words) — flush now
    if (ccQueue.trim()) {
      ccDisplayed += (ccDisplayed ? " " : "") + ccQueue.trim();
      ccQueue = "";
      _updateSubtitleDOM();
    }
    ccDoneTimer = setTimeout(clearSubtitle, 4500);
    ccTranscriptDone = false;
  }
  // else: interval is running; _revealChunk will drain and then set the timer
}

// Called when response.created fires — reset for the next response
function onSubtitleNewResponse() {
  clearTimeout(ccDoneTimer);
  clearInterval(ccRevealIv);
  ccRevealIv = null;
  ccQueue = "";
  ccDisplayed = "";
  ccTranscriptDone = false;
  subtitleText.textContent = "";
  subtitleText.style.transform = "";
}

function clearSubtitle() {
  clearTimeout(ccDoneTimer);
  clearInterval(ccRevealIv);
  ccRevealIv = null;
  ccDoneTimer = null;
  ccQueue = "";
  ccDisplayed = "";
  ccTranscriptDone = false;
  subtitleText.textContent = "";
  subtitleText.style.transform = "";
  subtitleArea.classList.remove("visible");
}
