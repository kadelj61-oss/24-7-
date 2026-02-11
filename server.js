require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const { initializeGCS } = require('./config/gcs');
const recordingsRouter = require('./routes/recordings');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static files from public directory
app.use(express.static(path.join(__dirname, 'public')));

// Initialize Google Cloud Storage
let gcsConfig;
try {
  gcsConfig = initializeGCS();
  app.locals.gcsBucket = gcsConfig.bucket;
  console.log('Google Cloud Storage initialized successfully');
} catch (error) {
  console.error('Warning: Google Cloud Storage initialization failed:', error.message);
  console.error('The /recordings endpoint will not function without valid GCS configuration');
}

// Routes
app.use('/recordings', recordingsRouter);

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    gcsConfigured: !!gcsConfig
  });
});

// Root endpoint - redirect to camera interface
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    path: req.path
  });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({
    error: 'Internal Server Error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Camera interface: http://localhost:${PORT}`);
  console.log(`Recordings endpoint: http://localhost:${PORT}/recordings`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});

module.exports = app;
