// static/js/difficulty-setting.js

document.addEventListener("DOMContentLoaded", () => {
  const select = document.getElementById("difficulty-select");

  if (!select) return;

  select.addEventListener("change", async (event) => {
    const difficulty = event.target.value;

    try {
      const response = await fetch("/api/update_difficulty", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ difficulty }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result = await response.json();
      console.log("Difficulty updated:", result.message);
    } catch (err) {
      console.error("Failed to update difficulty:", err);
    }
  });
});
