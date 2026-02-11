const express = require('express');
const multer = require('multer');
const { uploadToGCS } = require('../config/gcs');

const router = express.Router();

// Configure multer for memory storage (files will be uploaded to GCS from memory)
const storage = multer.memoryStorage();

// File filter function
const fileFilter = (req, file, cb) => {
  const allowedMimeTypes = process.env.ALLOWED_MIME_TYPES 
    ? process.env.ALLOWED_MIME_TYPES.split(',')
    : ['video/mp4', 'video/webm', 'image/jpeg', 'image/png', 'image/jpg'];

  if (allowedMimeTypes.includes(file.mimetype)) {
    cb(null, true);
  } else {
    cb(new Error(`Invalid file type. Allowed types: ${allowedMimeTypes.join(', ')}`), false);
  }
};

// Configure multer middleware
const upload = multer({
  storage: storage,
  fileFilter: fileFilter,
  limits: {
    fileSize: parseInt(process.env.MAX_FILE_SIZE || 104857600) // Default 100MB
  }
});

/**
 * POST /recordings
 * Upload a recording (photo or video) to Google Cloud Storage
 */
router.post('/', upload.single('recording'), async (req, res) => {
  try {
    // Validate file was uploaded
    if (!req.file) {
      return res.status(400).json({
        success: false,
        error: 'No file uploaded'
      });
    }

    // Get GCS bucket from app locals (set by server.js)
    const bucket = req.app.locals.gcsBucket;
    
    if (!bucket) {
      return res.status(500).json({
        success: false,
        error: 'Cloud storage not configured'
      });
    }

    // Generate destination path with timestamp
    const timestamp = Date.now();
    const fileExtension = req.file.originalname.split('.').pop();
    const destinationPath = `recordings/${timestamp}-${req.file.originalname}`;

    // Upload to GCS
    console.log(`Uploading ${req.file.originalname} (${req.file.size} bytes) to GCS...`);
    const uploadResult = await uploadToGCS(bucket, req.file, destinationPath);

    // Return success response
    res.status(201).json({
      success: true,
      message: 'File uploaded successfully',
      data: {
        filename: uploadResult.filename,
        url: uploadResult.url,
        size: uploadResult.size,
        mimetype: uploadResult.mimetype,
        uploadedAt: uploadResult.uploadedAt
      }
    });

  } catch (error) {
    console.error('Upload error:', error);

    // Handle specific multer errors
    if (error instanceof multer.MulterError) {
      if (error.code === 'LIMIT_FILE_SIZE') {
        return res.status(413).json({
          success: false,
          error: 'File too large',
          maxSize: process.env.MAX_FILE_SIZE || 104857600
        });
      }
      return res.status(400).json({
        success: false,
        error: error.message
      });
    }

    // Handle other errors
    res.status(500).json({
      success: false,
      error: 'Failed to upload file',
      details: error.message
    });
  }
});

/**
 * GET /recordings
 * Health check endpoint for recordings route
 */
router.get('/', (req, res) => {
  res.json({
    status: 'ok',
    endpoint: '/recordings',
    methods: ['POST'],
    description: 'Upload recordings to Google Cloud Storage'
  });
});

module.exports = router;
