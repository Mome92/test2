document.addEventListener('DOMContentLoaded', () => {
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const output = document.getElementById('output');
    let mediaRecorder;
    let audioChunks = [];
    let socket;

    // Initialize Socket.IO connection
    function initializeSocket() {
        // Connect to the server
        socket = io();

        socket.on('connect', () => {
            console.log('Connected to server');
        });

        socket.on('disconnect', () => {
            console.log('Disconnected from server');
        });

        socket.on('transcript', (data) => {
            if (data.is_partial) {
                // Update the last transcription
                const lastTranscript = output.lastElementChild;
                if (lastTranscript && lastTranscript.classList.contains('partial')) {
                    lastTranscript.textContent = data.text;
                } else {
                    const p = document.createElement('p');
                    p.classList.add('partial');
                    p.textContent = data.text;
                    output.appendChild(p);
                }
            } else {
                // Create a new final transcription
                const lastTranscript = output.lastElementChild;
                if (lastTranscript && lastTranscript.classList.contains('partial')) {
                    lastTranscript.remove();
                }
                const p = document.createElement('p');
                p.textContent = data.text;
                output.appendChild(p);
            }
        });

        socket.on('error', (data) => {
            console.error('Server error:', data.message);
            const p = document.createElement('p');
            p.style.color = 'red';
            p.textContent = `Error: ${data.message}`;
            output.appendChild(p);
        });
    }

    // Initialize audio recording
    async function initializeRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                const reader = new FileReader();
                reader.readAsDataURL(audioBlob);
                reader.onloadend = () => {
                    const base64Audio = reader.result;
                    socket.emit('audio_data', { audio: base64Audio });
                };
                audioChunks = [];
            };

        } catch (error) {
            console.error('Error accessing microphone:', error);
            const p = document.createElement('p');
            p.style.color = 'red';
            p.textContent = `Error accessing microphone: ${error.message}`;
            output.appendChild(p);
        }
    }

    // Start recording
    startButton.addEventListener('click', () => {
        if (!socket) {
            initializeSocket();
        }
        if (mediaRecorder && mediaRecorder.state === 'inactive') {
            audioChunks = [];
            mediaRecorder.start(1000); // Collect data every second
            startButton.disabled = true;
            stopButton.disabled = false;
            document.body.classList.add('recording');
        }
    });

    // Stop recording
    stopButton.addEventListener('click', () => {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            startButton.disabled = false;
            stopButton.disabled = true;
            document.body.classList.remove('recording');
        }
    });

    // Initialize recording capabilities when the page loads
    initializeRecording();
}); 