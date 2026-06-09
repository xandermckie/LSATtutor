/* Chat interface — handles message submission and thread rendering. */

(function () {
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const thread = document.getElementById("chatThread");
  const sendBtn = document.getElementById("sendBtn");

  if (!form) return;

  function appendMessage(role, text) {
    /* Add a new message bubble to the thread. */
    const div = document.createElement("div");
    div.className = "chat-message chat-message--" + role;
    div.textContent = text;
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
        if (!res.ok) throw new Error("Request failed with status " + res.status);
        return res.json();
      })
      .then(function (data) {
        thread.removeChild(loadingBubble);
        if (data.error) {
          appendMessage("system", "Error: " + data.error);
        } else {
          appendMessage("assistant", data.response);
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

  /* Allow Shift+Enter for newline, Enter to submit. */
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event("submit"));
    }
  });
})();
