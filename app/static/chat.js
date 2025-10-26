// JavaScript for handling chat interactions

// Function to get CSRF token from cookies
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

document.addEventListener("DOMContentLoaded", () => {
    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("message-input");
    const chatButton = document.getElementById("send-button");
    const csrftoken = getCookie('csrftoken');

    // Handle send button click
    chatButton.addEventListener("click", sendMessage);

    // Handle Enter key press
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendMessage();
        }
    });

    function sendMessage() {
        const userMessage = chatInput.value.trim();
        if (userMessage) {
            appendMessage("You", userMessage, "user-message");
            chatInput.value = "";

            // Send user message to the server
            fetch("/handle_user_input", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": csrftoken,
                },
                body: new URLSearchParams({ message: userMessage }),
            })
                .then((response) => response.json())
                .then((data) => {
                    if (data.response) {
                        appendMessage("AI", data.response, "ai-message");
                    } else {
                        appendMessage("Error", "Failed to get a response from the server.", "error-message");
                    }
                })
                .catch(() => {
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
});