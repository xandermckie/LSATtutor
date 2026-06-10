/* Chat interface — handles message submission and thread rendering. */

(function () {
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const thread = document.getElementById("chatThread");
  const sendBtn = document.getElementById("sendBtn");
  const quotaLabel = document.getElementById("quotaLabel");

  function updateQuota(remaining) {
    if (!quotaLabel) return;
    if (remaining === undefined || remaining === null) return;
    quotaLabel.textContent = remaining + " of 25 messages remaining today";
    quotaLabel.className = "chat-quota" + (remaining <= 5 ? " chat-quota--low" : "");
  }

  if (!form) return;

  /* Render prior chat history inlined by the server — no extra round-trip needed. */
  (window.__ratioHistory || []).forEach(function (turn) {
    appendMessage(turn.role, turn.content);
  });

  function appendMessage(role, text) {
    /* Add a new message bubble to the thread. */
    const div = document.createElement("div");
    div.className = "chat-message chat-message--" + role;
    if (role === "assistant" && typeof marked !== "undefined" && typeof DOMPurify !== "undefined") {
      div.innerHTML = DOMPurify.sanitize(marked.parse(text));
    } else {
      div.textContent = text;
    }
    thread.appendChild(div);
    thread.scrollTop = thread.scrollHeight;
    return div;
  }

  function setLoading(on) {
    /* Toggle the send button disabled state. */
    sendBtn.disabled = on;
    sendBtn.textContent = on ? "Sending..." : "Send";
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    const message = input.value.trim();
    if (!message) return;

    if (message.length > 3000) {
      appendMessage("system", "Message too long. Please keep messages under 3,000 characters.");
      return;
    }

    appendMessage("user", message);
    input.value = "";
    setLoading(true);

    const loadingBubble = appendMessage("loading", "Thinking...");

    fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        }).catch(function () {
          return { ok: false, status: res.status, data: null };
        });
      })
      .then(function (result) {
        thread.removeChild(loadingBubble);
        if (!result.ok) {
          var msg = (result.data && result.data.error)
            ? result.data.error
            : "Something went wrong. Please try again.";
          appendMessage("system", msg);
          return;
        }
        if (result.data.error) {
          appendMessage("system", result.data.error);
        } else {
          appendMessage("assistant", result.data.response);
          updateQuota(result.data.remaining);
        }
      })
      .catch(function (err) {
        thread.removeChild(loadingBubble);
        appendMessage("system", "Something went wrong. Please try again.");
        console.error(err);
      })
      .finally(function () {
        setLoading(false);
      });
  });

  /* Auto-expand textarea as user types. */
  input.addEventListener("input", function () {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  });

  /* Allow Shift+Enter for newline, Enter to submit. */
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event("submit"));
    }
  });
})();
