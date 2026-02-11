// Camera Recorder JavaScript
class CameraRecorder {
    constructor() {
        this.videoElement = document.getElementById('videoPreview');
        this.canvasElement = document.getElementById('canvas');
        this.recordingIndicator = document.getElementById('recordingIndicator');
        this.statusMessage = document.getElementById('statusMessage');
        this.uploadProgress = document.getElementById('uploadProgress');
        this.progressFill = document.getElementById('progressFill');
        this.uploadStatus = document.getElementById('uploadStatus');
        this.recordingsList = document.getElementById('recordingsList');

        this.stream = null;
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.recordings = [];

        this.initializeButtons();
    }

    initializeButtons() {
        document.getElementById('startCameraBtn').addEventListener('click', () => this.startCamera());
        document.getElementById('stopCameraBtn').addEventListener('click', () => this.stopCamera());
        document.getElementById('capturePhotoBtn').addEventListener('click', () => this.capturePhoto());
        document.getElementById('startRecordingBtn').addEventListener('click', () => this.startRecording());
        document.getElementById('stopRecordingBtn').addEventListener('click', () => this.stopRecording());
    }

    async startCamera() {
        try {
            this.showStatus('Requesting camera access...', 'info');

            const constraints = {
                video: {
                    width: { ideal: 1920 },
                    height: { ideal: 1080 }
                },
                audio: true
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.videoElement.srcObject = this.stream;

            // Update button states
            document.getElementById('startCameraBtn').disabled = true;
            document.getElementById('stopCameraBtn').disabled = false;
            document.getElementById('capturePhotoBtn').disabled = false;
            document.getElementById('startRecordingBtn').disabled = false;

            this.showStatus('Camera started successfully!', 'success');
            setTimeout(() => this.hideStatus(), 3000);

        } catch (error) {
            console.error('Camera error:', error);
            this.showStatus(`Failed to access camera: ${error.message}`, 'error');
        }
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.videoElement.srcObject = null;
            this.stream = null;

            // Update button states
            document.getElementById('startCameraBtn').disabled = false;
            document.getElementById('stopCameraBtn').disabled = true;
            document.getElementById('capturePhotoBtn').disabled = true;
            document.getElementById('startRecordingBtn').disabled = true;
            document.getElementById('stopRecordingBtn').disabled = true;

            this.showStatus('Camera stopped', 'info');
            setTimeout(() => this.hideStatus(), 2000);
        }
    }

    async capturePhoto() {
        try {
            this.showStatus('Capturing photo...', 'info');

            // Set canvas dimensions to match video
            this.canvasElement.width = this.videoElement.videoWidth;
            this.canvasElement.height = this.videoElement.videoHeight;

            // Draw current video frame to canvas
            const context = this.canvasElement.getContext('2d');
            context.drawImage(this.videoElement, 0, 0);

            // Convert canvas to blob with explicit JPEG format
            const blob = await new Promise(resolve => {
                this.canvasElement.toBlob(resolve, 'image/jpeg', 0.95);
            });

            // Create filename with timestamp
            const filename = `photo_${Date.now()}.jpg`;

            // Create a proper File object with explicit MIME type
            const file = new File([blob], filename, {
                type: 'image/jpeg',
                lastModified: Date.now()
            });

            // Upload the photo
            await this.uploadFile(file, filename);

        } catch (error) {
            console.error('Photo capture error:', error);
            this.showStatus(`Failed to capture photo: ${error.message}`, 'error');
        }
    }

    async startRecording() {
        try {
            this.showStatus('Starting video recording...', 'info');
            this.recordedChunks = [];

            // Determine supported MIME type
            const mimeTypes = [
                'video/webm;codecs=vp9',
                'video/webm;codecs=vp8',
                'video/webm',
                'video/mp4'
            ];

            let selectedMimeType = '';
            for (const mimeType of mimeTypes) {
                if (MediaRecorder.isTypeSupported(mimeType)) {
                    selectedMimeType = mimeType;
                    break;
                }
            }

            if (!selectedMimeType) {
                throw new Error('No supported video format found');
            }

            // Create MediaRecorder
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: selectedMimeType,
                videoBitsPerSecond: 2500000
            });

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                // Create blob from recorded chunks
                const blob = new Blob(this.recordedChunks, {
                    type: selectedMimeType
                });

                // Determine file extension
                const extension = selectedMimeType.includes('webm') ? 'webm' : 'mp4';
                const filename = `video_${Date.now()}.${extension}`;

                // Create a proper File object with explicit MIME type
                const file = new File([blob], filename, {
                    type: selectedMimeType,
                    lastModified: Date.now()
                });

                // Upload the video
                await this.uploadFile(file, filename);

                this.recordedChunks = [];
            };

            // Start recording
            this.mediaRecorder.start();

            // Update UI
            this.recordingIndicator.classList.add('active');
            document.getElementById('startRecordingBtn').disabled = true;
            document.getElementById('stopRecordingBtn').disabled = false;
            document.getElementById('capturePhotoBtn').disabled = true;

            this.showStatus('Recording started!', 'success');
            setTimeout(() => this.hideStatus(), 2000);

        } catch (error) {
            console.error('Recording error:', error);
            this.showStatus(`Failed to start recording: ${error.message}`, 'error');
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();

            // Update UI
            this.recordingIndicator.classList.remove('active');
            document.getElementById('startRecordingBtn').disabled = false;
            document.getElementById('stopRecordingBtn').disabled = true;
            document.getElementById('capturePhotoBtn').disabled = false;

            this.showStatus('Recording stopped. Uploading...', 'info');
        }
    }

    async uploadFile(file, filename) {
        try {
            // Show upload progress
            this.uploadProgress.classList.add('show');
            this.progressFill.style.width = '0%';
            this.progressFill.textContent = '0%';
            this.uploadStatus.textContent = `Uploading ${filename}...`;

            // Create FormData and explicitly specify filename to ensure proper extension
            const formData = new FormData();
            formData.append('recording', file, filename);

            console.log(`Uploading file: ${filename}, MIME type: ${file.type}`);

            // Upload with fetch API
            const response = await fetch('/recordings', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Upload failed');
            }

            const result = await response.json();

            // Simulate progress (since we can't track actual upload progress with fetch easily)
            this.progressFill.style.width = '100%';
            this.progressFill.textContent = '100%';
            this.uploadStatus.textContent = 'Upload complete!';

            // Add to recordings list
            this.addRecordingToList(result.data);

            // Hide progress after delay
            setTimeout(() => {
                this.uploadProgress.classList.remove('show');
            }, 2000);

            this.showStatus('File uploaded successfully!', 'success');
            setTimeout(() => this.hideStatus(), 3000);

        } catch (error) {
            console.error('Upload error:', error);
            this.uploadProgress.classList.remove('show');
            this.showStatus(`Upload failed: ${error.message}`, 'error');
        }
    }

    addRecordingToList(recording) {
        // Add to recordings array
        this.recordings.unshift(recording);

        // Update the list
        if (this.recordings.length === 1) {
            this.recordingsList.innerHTML = '';
        }

        const recordingItem = document.createElement('div');
        recordingItem.className = 'recording-item';

        const isVideo = recording.mimetype.startsWith('video/');
        const fileSize = this.formatFileSize(recording.size);
        const uploadTime = new Date(recording.uploadedAt).toLocaleString();

        recordingItem.innerHTML = `
            <div class="recording-info">
                <strong>${isVideo ? '🎥' : '📷'} ${recording.filename}</strong>
                <small>${fileSize} • ${uploadTime}</small>
            </div>
            <a href="${recording.url}" target="_blank" class="recording-link">
                View
            </a>
        `;

        this.recordingsList.insertBefore(recordingItem, this.recordingsList.firstChild);
    }

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    showStatus(message, type) {
        this.statusMessage.textContent = message;
        this.statusMessage.className = `status status-${type} show`;
    }

    hideStatus() {
        this.statusMessage.classList.remove('show');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CameraRecorder();
});
