// JavaScript for handling chat interactions

/**
 * Get CSRF token from cookies
 * @param {string} name - The name of the cookie to retrieve
 * @returns {string|null} The cookie value or null if not found
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

let currentSessionId = null;
const csrftoken = getCookie('csrftoken');

document.addEventListener("DOMContentLoaded", () => {
    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("message-input");
    const chatButton = document.getElementById("send-button");
    const newSessionBtn = document.getElementById("new-session-btn");
    const deleteSessionBtn = document.getElementById("delete-session-btn");
    const sessionList = document.getElementById("session-list");
    const sessionTitle = document.getElementById("session-title");
    
    // Settings modal elements
    const settingsBtn = document.getElementById("settings-btn");
    const settingsModal = document.getElementById("settings-modal");
    const closeModal = document.querySelector(".close");
    const saveSettingsBtn = document.getElementById("save-settings-btn");
    const clearSettingsBtn = document.getElementById("clear-settings-btn");
    const personalityPromptInput = document.getElementById("personality-prompt-input");

    // Load sessions on page load
    loadSessions();
    
    // Load personality prompt on page load
    loadPersonalityPrompt();

    // Handle send button click
    chatButton.addEventListener("click", sendMessage);

    // Handle Enter key press
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendMessage();
        }
    });

    // Handle new session button
    newSessionBtn.addEventListener("click", createNewSession);

    // Handle delete session button
    deleteSessionBtn.addEventListener("click", deleteCurrentSession);
    
    // Handle settings button
    settingsBtn.addEventListener("click", () => {
        settingsModal.style.display = "block";
    });
    
    // Handle close modal
    closeModal.addEventListener("click", () => {
        settingsModal.style.display = "none";
    });
    
    // Close modal when clicking outside
    window.addEventListener("click", (event) => {
        if (event.target === settingsModal) {
            settingsModal.style.display = "none";
        }
    });
    
    // Handle save settings
    saveSettingsBtn.addEventListener("click", savePersonalityPrompt);
    
    // Handle clear settings
    clearSettingsBtn.addEventListener("click", clearPersonalityPrompt);

    function sendMessage() {
        const userMessage = chatInput.value.trim();
        if (userMessage) {
            appendMessage("You", userMessage, "user-message");
            chatInput.value = "";

            // Show loading indicator
            const loadingMessage = showLoadingIndicator();

            // Send user message to the server
            fetch("/handle_user_input", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": csrftoken,
                },
                body: new URLSearchParams({ 
                    message: userMessage,
                    session_id: currentSessionId || ""
                }),
            })
                .then((response) => response.json())
                .then((data) => {
                    // Remove loading indicator
                    removeLoadingIndicator(loadingMessage);
                    
                    if (data.response) {
                        appendMessage("AI", data.response, "ai-message");
                        // Update current session ID if it was created
                        if (data.session_id && !currentSessionId) {
                            currentSessionId = data.session_id;
                            updateSessionTitle();
                            loadSessions(); // Refresh session list
                        }
                    } else {
                        appendMessage("Error", "Failed to get a response from the server.", "error-message");
                    }
                })
                .catch(() => {
                    // Remove loading indicator
                    removeLoadingIndicator(loadingMessage);
                    appendMessage("Error", "An error occurred while communicating with the server.", "error-message");
                });
        }
    }

    function appendMessage(sender, message, className) {
        const messageElement = document.createElement("div");
        messageElement.classList.add("message", className);
        messageElement.innerHTML = `<strong>${sender}:</strong> ${message}`;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showLoadingIndicator() {
        const loadingElement = document.createElement("div");
        loadingElement.classList.add("message", "loading-message");
        loadingElement.innerHTML = `
            <strong>AI:</strong> 
            <span>Thinking</span>
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        chatMessages.appendChild(loadingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return loadingElement;
    }

    function removeLoadingIndicator(loadingElement) {
        if (loadingElement && loadingElement.parentNode) {
            loadingElement.parentNode.removeChild(loadingElement);
        }
    }

    function createNewSession() {
        fetch("/api/sessions/create", {
            method: "POST",
            headers: {
                "X-CSRFToken": csrftoken,
            },
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.session_id) {
                    currentSessionId = data.session_id;
                    chatMessages.innerHTML = '<div class="empty-state">Start a new conversation...</div>';
                    updateSessionTitle();
                    loadSessions();
                }
            })
            .catch((error) => {
                console.error("Error creating session:", error);
            });
    }

    function loadSessions() {
        fetch("/api/sessions/list")
            .then((response) => response.json())
            .then((data) => {
                sessionList.innerHTML = "";
                
                if (data.sessions.length === 0) {
                    sessionList.innerHTML = '<div class="empty-state">No sessions yet.<br>Click + to start!</div>';
                    return;
                }

                data.sessions.forEach((session) => {
                    const sessionItem = document.createElement("div");
                    sessionItem.classList.add("session-item");
                    if (session.id === currentSessionId) {
                        sessionItem.classList.add("active");
                    }

                    const date = new Date(session.started_at);
                    const timeStr = date.toLocaleString();
                    
                    sessionItem.innerHTML = `
                        <div class="session-time">${timeStr}</div>
                        <div class="session-preview">${session.last_message || "No messages yet"}</div>
                        <div class="session-count">${session.message_count} message(s)</div>
                    `;

                    sessionItem.addEventListener("click", () => {
                        loadSessionHistory(session.id);
                    });

                    sessionList.appendChild(sessionItem);
                });
            })
            .catch((error) => {
                console.error("Error loading sessions:", error);
            });
    }

    function loadSessionHistory(sessionId) {
        fetch(`/api/sessions/${sessionId}/history`)
            .then((response) => response.json())
            .then((data) => {
                currentSessionId = sessionId;
                chatMessages.innerHTML = "";

                if (data.messages.length === 0) {
                    chatMessages.innerHTML = '<div class="empty-state">No messages in this session yet.</div>';
                } else {
                    data.messages.forEach((msg) => {
                        const className = msg.is_user ? "user-message" : "ai-message";
                        const sender = msg.is_user ? "You" : "AI";
                        appendMessage(sender, msg.message, className);
                    });
                }

                updateSessionTitle();
                loadSessions(); // Refresh to update active state
            })
            .catch((error) => {
                console.error("Error loading session history:", error);
            });
    }

    function deleteCurrentSession() {
        if (!currentSessionId) {
            alert("No session selected to delete.");
            return;
        }

        if (!confirm("Are you sure you want to delete this session?")) {
            return;
        }

        fetch(`/api/sessions/${currentSessionId}/delete`, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrftoken,
            },
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    currentSessionId = null;
                    chatMessages.innerHTML = '<div class="empty-state">Session deleted. Create a new session to start chatting.</div>';
                    updateSessionTitle();
                    loadSessions();
                }
            })
            .catch((error) => {
                console.error("Error deleting session:", error);
            });
    }

    function updateSessionTitle() {
        if (currentSessionId) {
            sessionTitle.textContent = `Session #${currentSessionId}`;
        } else {
            sessionTitle.textContent = "AI Chat Assistant";
        }
    }
    
    function loadPersonalityPrompt() {
        fetch("/api/personality/get")
            .then((response) => response.json())
            .then((data) => {
                if (data.personality_prompt) {
                    personalityPromptInput.value = data.personality_prompt;
                }
            })
            .catch((error) => {
                console.error("Error loading personality prompt:", error);
            });
    }
    
    function savePersonalityPrompt() {
        const personalityPrompt = personalityPromptInput.value.trim();
        
        fetch("/api/personality/update", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": csrftoken,
            },
            body: new URLSearchParams({ 
                personality_prompt: personalityPrompt
            }),
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    settingsModal.style.display = "none";
                    alert("Personality prompt saved successfully!");
                } else {
                    alert("Failed to save personality prompt.");
                }
            })
            .catch((error) => {
                console.error("Error saving personality prompt:", error);
                alert("An error occurred while saving.");
            });
    }
    
    function clearPersonalityPrompt() {
        if (!confirm("Are you sure you want to clear the personality prompt?")) {
            return;
        }
        
        fetch("/api/personality/update", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": csrftoken,
            },
            body: new URLSearchParams({ 
                personality_prompt: ""
            }),
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    personalityPromptInput.value = "";
                    alert("Personality prompt cleared successfully!");
                } else {
                    alert("Failed to clear personality prompt.");
                }
            })
            .catch((error) => {
                console.error("Error clearing personality prompt:", error);
                alert("An error occurred while clearing.");
            });
    }
});