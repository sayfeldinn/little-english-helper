/**
 * script.js
 * ---------
 * Handles all frontend interactivity:
 *  - Reading the textarea input
 *  - Calling POST /check on the backend
 *  - Toggling the loading spinner
 *  - Displaying feedback or error messages
 *  - Disabling/re-enabling the button during the request
 */

// Grab references to all the DOM elements we need once, up front.
const checkButton = document.getElementById("check-button");
const buttonText = document.getElementById("button-text");
const sentenceInput = document.getElementById("sentence-input");
const loadingIndicator = document.getElementById("loading-indicator");
const outputCard = document.getElementById("output-card");
const correctedCell = document.getElementById("corrected-cell");
const correctedText = document.getElementById("corrected-text");
const feedbackText = document.getElementById("feedback-text");
const errorMessage = document.getElementById("error-message");

/** Hides both the output card and the error box. */
function hideResults() {
    outputCard.classList.add("hidden");
    errorMessage.classList.add("hidden");
}

/** Shows the AI feedback and corrected sentence in the output card. */
function showFeedback(data) {
    if (data.corrected_sentence) {
        correctedText.textContent = data.corrected_sentence;
        correctedCell.classList.remove("hidden");
    } else {
        correctedCell.classList.add("hidden");
    }
    feedbackText.textContent = data.feedback;
    outputCard.classList.remove("hidden");
    errorMessage.classList.add("hidden");
}

/** Shows a friendly error message. */
function showError(text) {
    errorMessage.textContent = text;
    errorMessage.classList.remove("hidden");
    outputCard.classList.add("hidden");
}

/** Checks if input would waste an API call. Returns an error string or null. */
function validateSentence(sentence) {
    if (/^\d+$/.test(sentence)) {
        return "That's just numbers! Try writing a sentence with words.";
    }
    if (/^[\p{Emoji}\s]+$/u.test(sentence)) {
        return "Those are emojis, not a sentence! Try some English words.";
    }
    if (sentence.length < 2) {
        return "That's too short! Write a full sentence.";
    }
    if (!/[a-zA-Z]/.test(sentence)) {
        return "I don't see any English letters! Please type a sentence.";
    }
    return null;
}

/** Toggles the loading spinner + disables/enables the button. */
function setLoading(isLoading) {
    loadingIndicator.classList.toggle("hidden", !isLoading);
    checkButton.disabled = isLoading;
    buttonText.textContent = isLoading ? "Checking..." : "Check My Sentence ✨";
}

/**
 * Main handler: called when the user clicks "Check My Sentence".
 */
async function handleCheckSentence() {
    const sentence = sentenceInput.value.trim();

    // Basic client-side validation before even calling the backend.
    if (!sentence) {
        showError("Please type a sentence before checking it!");
        return;
    }

    const validationError = validateSentence(sentence);
    if (validationError) {
        showError(validationError);
        return;
    }

    hideResults();
    setLoading(true);

    try {
        const response = await fetch("/check", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ sentence }),
        });

        // The backend always returns JSON, even on errors, so we can parse
        // the body first and then decide what to do based on response.ok.
        const data = await response.json();

        if (!response.ok) {
            showError(data.error || "Something went wrong. Please try again.");
            return;
        }

        showFeedback(data);

    } catch (networkError) {
        // This branch triggers on genuine network failures (e.g. offline,
        // DNS failure) since fetch() itself throws in those cases.
        console.error("Network error calling /check:", networkError);
        showError(
            "We couldn't reach the server. Please check your internet connection and try again. 🌐"
        );
    } finally {
        setLoading(false);
    }
}

checkButton.addEventListener("click", handleCheckSentence);

// Optional nice-to-have: allow Ctrl+Enter / Cmd+Enter to submit from the textarea.
sentenceInput.addEventListener("keydown", (event) => {
    const isSubmitShortcut = (event.ctrlKey || event.metaKey) && event.key === "Enter";
    if (isSubmitShortcut) {
        event.preventDefault();
        handleCheckSentence();
    }
});
