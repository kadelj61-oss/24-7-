const { Storage } = require('@google-cloud/storage');
const path = require('path');

/**
 * Initialize and configure Google Cloud Storage client
 * @returns {Object} Object containing storage client and bucket
 */
function initializeGCS() {
  try {
    // Configuration from environment variables
    const projectId = process.env.GCS_PROJECT_ID;
    const bucketName = process.env.GCS_BUCKET_NAME;
    const keyfilePath = process.env.GCS_KEYFILE_PATH;

    if (!projectId || !bucketName) {
      throw new Error('GCS_PROJECT_ID and GCS_BUCKET_NAME must be set in environment variables');
    }

    // Initialize Storage client
    const storageOptions = {
      projectId: projectId
    };

    // Add keyfile if provided
    if (keyfilePath) {
      storageOptions.keyFilename = path.resolve(keyfilePath);
    }

    const storage = new Storage(storageOptions);
    const bucket = storage.bucket(bucketName);

    console.log(`GCS initialized: Project=${projectId}, Bucket=${bucketName}`);

    return {
      storage,
      bucket,
      bucketName
    };
  } catch (error) {
    console.error('Failed to initialize GCS:', error.message);
    throw error;
  }
}

/**
 * Upload a file to Google Cloud Storage
 * @param {Object} bucket - GCS bucket instance
 * @param {Object} file - File object from multer
 * @param {string} destinationPath - Destination path in GCS
 * @returns {Promise<Object>} Upload result with public URL
 */
async function uploadToGCS(bucket, file, destinationPath) {
  try {
    const blob = bucket.file(destinationPath);
    const blobStream = blob.createWriteStream({
      resumable: false,
      metadata: {
        contentType: file.mimetype,
        metadata: {
          originalName: file.originalname,
          uploadedAt: new Date().toISOString()
        }
      }
    });

    return new Promise((resolve, reject) => {
      blobStream.on('error', (err) => {
        console.error('Upload error:', err);
        reject(err);
      });

      blobStream.on('finish', async () => {
        try {
          // Make the file public (optional - remove if you want private files)
          await blob.makePublic();

          const publicUrl = `https://storage.googleapis.com/${bucket.name}/${blob.name}`;
          
          resolve({
            filename: blob.name,
            url: publicUrl,
            size: file.size,
            mimetype: file.mimetype,
            uploadedAt: new Date().toISOString()
          });
        } catch (err) {
          reject(err);
        }
      });

      blobStream.end(file.buffer);
    });
  } catch (error) {
    console.error('GCS upload failed:', error);
    throw error;
  }
}

module.exports = {
  initializeGCS,
  uploadToGCS
};
