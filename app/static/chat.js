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
                        
                        // If summary was updated, refresh the session list to show new summary
                        if (data.summary_updated) {
                            loadSessions();
                        }
                        
                        // If personality was auto-updated, show notification
                        if (data.personality_updated) {
                            showPersonalityUpdateNotification();
                            loadPersonalityPrompt(); // Refresh personality prompt in settings
                        }
                        
                        // If personality suggestion is available, check and display it
                        if (data.personality_suggestion_available) {
                            checkPersonalitySuggestion(currentSessionId);
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
        if (loadingElement) {
            loadingElement.remove();
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
                        <div class="session-preview">${session.summary || "No messages yet"}</div>
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
    
    // Periodically check for session inactivity and proactive suggestions
    let inactivityCheckInterval = null;
    let personalityCheckInterval = null;
    let newMessagesCheckInterval = null;
    
    function startInactivityMonitoring() {
        // Clear any existing interval
        if (inactivityCheckInterval) {
            clearInterval(inactivityCheckInterval);
        }
        
        // Check every 2 minutes for inactivity
        inactivityCheckInterval = setInterval(() => {
            if (currentSessionId) {
                checkSessionInactivity(currentSessionId);
            }
        }, 120000); // 2 minutes in milliseconds
    }
    
    function startPersonalityMonitoring() {
        // Clear any existing interval
        if (personalityCheckInterval) {
            clearInterval(personalityCheckInterval);
        }
        
        // Check every 5 minutes for personality update suggestions
        personalityCheckInterval = setInterval(() => {
            if (currentSessionId) {
                checkPersonalitySuggestion(currentSessionId);
            }
        }, 300000); // 5 minutes in milliseconds
    }
    
    function startNewMessagesMonitoring() {
        // Clear any existing interval
        if (newMessagesCheckInterval) {
            clearInterval(newMessagesCheckInterval);
        }
        
        // Check every 30 seconds for new proactive messages
        newMessagesCheckInterval = setInterval(() => {
            if (currentSessionId) {
                checkForNewMessages(currentSessionId);
            }
        }, 30000); // 30 seconds in milliseconds
    }
    
    function checkSessionInactivity(sessionId) {
        fetch(`/api/sessions/${sessionId}/inactivity`)
            .then((response) => response.json())
            .then((data) => {
                if (data.action === 'continue' || data.action === 'new_topic') {
                    // Display the suggested message as a proactive AI message
                    if (data.suggested_message) {
                        appendMessage("AI (Proactive)", data.suggested_message, "ai-message proactive-message");
                    }
                }
            })
            .catch((error) => {
                console.error("Error checking inactivity:", error);
            });
    }
    
    function checkForNewMessages(sessionId) {
        fetch(`/api/sessions/${sessionId}/new-messages`)
            .then((response) => response.json())
            .then((data) => {
                if (data.has_new_messages && data.new_messages.length > 0) {
                    // Display new proactive messages with red dot indicator
                    data.new_messages.forEach((msg) => {
                        appendMessage("AI (Proactive)", msg.message, "ai-message proactive-message new-message");
                    });
                    
                    // Show red dot indicator on session
                    showNewMessageIndicator();
                    
                    // Acknowledge the messages
                    acknowledgeNewMessages(sessionId);
                }
            })
            .catch((error) => {
                console.error("Error checking new messages:", error);
            });
    }
    
    function acknowledgeNewMessages(sessionId) {
        fetch(`/api/sessions/${sessionId}/acknowledge-messages`, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrftoken,
            }
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    console.log("New messages acknowledged");
                }
            })
            .catch((error) => {
                console.error("Error acknowledging messages:", error);
            });
    }
    
    function showNewMessageIndicator() {
        // Add a visual indicator (red dot) to the session title or chat area
        const sessionTitle = document.getElementById('session-title');
        if (sessionTitle && !sessionTitle.querySelector('.new-message-dot')) {
            const dot = document.createElement('span');
            dot.className = 'new-message-dot';
            dot.style.cssText = 'display: inline-block; width: 8px; height: 8px; background-color: red; border-radius: 50%; margin-left: 8px;';
            sessionTitle.appendChild(dot);
            
            // Remove the dot after 5 seconds
            setTimeout(() => {
                dot.remove();
            }, 5000);
        }
    }
    
    function checkPersonalitySuggestion(sessionId) {
        fetch(`/api/sessions/${sessionId}/personality-suggestion`)
            .then((response) => response.json())
            .then((data) => {
                if (data.has_suggestion && data.suggestion && data.suggestion.should_update) {
                    displayPersonalitySuggestion(data.suggestion);
                }
            })
            .catch((error) => {
                console.error("Error checking personality suggestion:", error);
            });
    }
    
    function displayPersonalitySuggestion(suggestion) {
        // Check if a suggestion banner already exists
        if (document.getElementById('personality-suggestion-banner')) {
            return; // Don't show duplicate banners
        }
        
        // Create a banner to display the suggestion
        const banner = document.createElement('div');
        banner.id = 'personality-suggestion-banner';
        banner.className = 'personality-suggestion-banner';
        banner.innerHTML = `
            <div class="suggestion-content">
                <div class="suggestion-header">
                    <strong>💡 Personality Update Suggestion</strong>
                    <span class="confidence-badge">Confidence: ${(suggestion.confidence * 100).toFixed(0)}%</span>
                </div>
                <div class="suggestion-reason">${suggestion.reason}</div>
                <div class="suggestion-personality">
                    <strong>Suggested personality:</strong> "${suggestion.suggested_personality}"
                </div>
                <div class="suggestion-actions">
                    <button class="btn-apply" onclick="applyPersonalitySuggestion()">Apply</button>
                    <button class="btn-dismiss" onclick="dismissPersonalitySuggestion()">Dismiss</button>
                </div>
            </div>
        `;
        
        // Insert the banner at the top of the chat container
        const chatContainer = document.querySelector('.chat-container');
        chatContainer.insertBefore(banner, chatContainer.firstChild);
        
        // Store the suggestion for later use
        window.currentPersonalitySuggestion = suggestion;
    }
    
    window.applyPersonalitySuggestion = function() {
        if (!currentSessionId) return;
        
        fetch(`/api/sessions/${currentSessionId}/personality-update`, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrftoken,
            }
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    alert("Personality updated successfully!");
                    removeSuggestionBanner();
                    // Update the personality prompt input if settings modal is open
                    loadPersonalityPrompt();
                } else {
                    alert("Failed to apply personality update.");
                }
            })
            .catch((error) => {
                console.error("Error applying personality update:", error);
                alert("An error occurred while applying the update.");
            });
    };
    
    window.dismissPersonalitySuggestion = function() {
        if (!currentSessionId) return;
        
        fetch(`/api/sessions/${currentSessionId}/personality-dismiss`, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrftoken,
            }
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    removeSuggestionBanner();
                }
            })
            .catch((error) => {
                console.error("Error dismissing personality suggestion:", error);
            });
    };
    
    function removeSuggestionBanner() {
        const banner = document.getElementById('personality-suggestion-banner');
        if (banner) {
            banner.remove();
        }
        window.currentPersonalitySuggestion = null;
    }
    
    function showPersonalityUpdateNotification() {
        // Create a temporary notification banner
        const notification = document.createElement('div');
        notification.className = 'personality-update-notification';
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background-color: #4CAF50; color: white; padding: 15px 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 1000;';
        notification.innerHTML = `
            <strong>✅ Personality Auto-Updated!</strong>
            <p style="margin: 5px 0 0 0; font-size: 0.9em;">The AI personality has been automatically updated based on your conversation patterns.</p>
        `;
        
        document.body.appendChild(notification);
        
        // Remove after 5 seconds
        setTimeout(() => {
            notification.style.transition = 'opacity 0.5s';
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 500);
        }, 5000);
    }
    
    // Start monitoring when a session is active
    startInactivityMonitoring();
    startPersonalityMonitoring();
    startNewMessagesMonitoring();
});