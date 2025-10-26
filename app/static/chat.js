// JavaScript for handling chat interactions

document.addEventListener("DOMContentLoaded", () => {
    const chatMessages = document.querySelector(".chat-messages");
    const chatInput = document.querySelector(".chat-input input");
    const chatButton = document.querySelector(".chat-input button");

    chatButton.addEventListener("click", () => {
        const userMessage = chatInput.value.trim();
        if (userMessage) {
            appendMessage("You", userMessage);
            chatInput.value = "";

            // Send user message to the server
            fetch("/handle_user_input", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: new URLSearchParams({ message: userMessage }),
            })
                .then((response) => response.json())
                .then((data) => {
                    if (data.response) {
                        appendMessage("Model", data.response);
                    } else {
                        appendMessage("Error", "Failed to get a response from the server.");
                    }
                })
                .catch(() => {
                    appendMessage("Error", "An error occurred while communicating with the server.");
                });
        }
    });

    function appendMessage(sender, message) {
        const messageElement = document.createElement("div");
        messageElement.classList.add("message");
        messageElement.innerHTML = `<strong>${sender}:</strong> ${message}`;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});