document.addEventListener('DOMContentLoaded', function() {
    const promptInput = document.getElementById('promptInput');
    const submitBtn = document.getElementById('submitBtn');
    const outputDiv = document.getElementById('output');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const toggleLogBtn = document.getElementById('toggleLogBtn');
    const stepsLog = document.getElementById('steps-log');
    const statusUpdates = document.getElementById('statusUpdates');
    
    // API endpoint (relative URL since we're serving from Flask)
    const API_URL = '/api/browser-agent';
    
    // Toggle log visibility
    toggleLogBtn.addEventListener('click', function() {
        if (stepsLog.style.display === 'block') {
            stepsLog.style.display = 'none';
            toggleLogBtn.innerHTML = '<i class="fas fa-list"></i> Show Execution Log';
        } else {
            stepsLog.style.display = 'block';
            toggleLogBtn.innerHTML = '<i class="fas fa-list"></i> Hide Execution Log';
        }
    });
    
    // Set prompt from example
    window.setPrompt = function(prompt) {
        promptInput.value = prompt;
        // Scroll to the textarea
        promptInput.scrollIntoView({ behavior: 'smooth' });
        // Focus on the textarea
        promptInput.focus();
    };
    
    submitBtn.addEventListener('click', async function() {
        // Get the user's prompt
        const userPrompt = promptInput.value.trim();
        
        if (!userPrompt) {
            outputDiv.textContent = "Please enter a prompt.";
            return;
        }
        
        // Show loading indicator
        loadingIndicator.style.display = 'block';
        outputDiv.innerHTML = '<div class="searching-message"><i class="fas fa-search"></i> Processing your request...</div>';
        submitBtn.disabled = true;
        stepsLog.innerHTML = '';
        statusUpdates.innerHTML = '';
        
        // Add some fake status updates to show progress
        let statusMessages = [
            { message: "Opening browser...", icon: "fa-window-maximize" },
            { message: "Navigating to search page...", icon: "fa-compass" },
            { message: "Entering search parameters...", icon: "fa-keyboard" },
            { message: "Analyzing results...", icon: "fa-chart-bar" },
            { message: "Extracting data...", icon: "fa-file-alt" },
            { message: "Formatting results...", icon: "fa-paint-brush" }
        ];
        
        let currentStatus = 0;
        let statusInterval = setInterval(() => {
            if (currentStatus < statusMessages.length) {
                let msg = statusMessages[currentStatus];
                let statusHtml = `<div class="status-item"><i class="fas ${msg.icon}"></i> ${msg.message}</div>`;
                statusUpdates.innerHTML += statusHtml;
                statusUpdates.scrollTop = statusUpdates.scrollHeight;
                currentStatus++;
            } else {
                clearInterval(statusInterval);
            }
        }, 3000);
        
        try {
            // Make API call to the backend
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: userPrompt }),
            });
            
            // Clear the interval when the response is received
            clearInterval(statusInterval);
            
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Display the results (now as HTML)
            outputDiv.innerHTML = data.result;
            
        } catch (error) {
            outputDiv.innerHTML = `<div class="error-message"><i class="fas fa-exclamation-circle"></i> Error: ${error.message}</div>`;
            console.error('Error:', error);
        } finally {
            // Hide loading indicator and re-enable button
            loadingIndicator.style.display = 'none';
            submitBtn.disabled = false;
        }
    });
});