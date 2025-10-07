// tab_data.js

document.addEventListener("DOMContentLoaded", function () {
            // Map textarea IDs to parameter names your backend expects
            const paramMap = {
                "param-style": "writing_style",
                "param-world": "world_setting",
                "param-rules": "rules",
                "param-characters": "characters",
                "param-player": "player"
            };

            // Attach listeners to each textarea
            Object.keys(paramMap).forEach(id => {
                const el = document.getElementById(id);
                if (!el) return;

                let timeout;
                el.addEventListener("input", function () {
                    clearTimeout(timeout);
                    timeout = setTimeout(() => {
                        sendUpdate(paramMap[id], el.value);
                    }, 800); // debounce: wait 0.8s after typing stops
                });
            });

            function sendUpdate(parameter, value) {
                fetch("/update_story_parameter", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ parameter, value })
                })
                .then(res => {
                    if (!res.ok) throw new Error("Network response was not ok");
                    return res.json();
                })
                .then(data => {
                    console.log(`Updated ${parameter}:`, data);
                })
                .catch(err => {
                    console.error(`Error updating ${parameter}:`, err);
                });
            }
        });