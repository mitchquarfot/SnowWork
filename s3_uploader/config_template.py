# Configuration Template for S3 Uploader Streamlit App
# Copy this to config.py and fill in your actual values

# AWS Configuration
AWS_ACCESS_KEY_ID = "YOUR_AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "YOUR_AWS_SECRET_ACCESS_KEY" 
AWS_REGION = "us-west-2"

# S3 Configuration
S3_BUCKET_NAME = "your-bucket-name"

# Upload Configuration
DEFAULT_EXPIRES_IN = 3600  # Presigned URL expiration time in seconds (1 hour)
MAX_FILE_SIZE_MB = 100     # Maximum file size in MB (adjust as needed)
ALLOWED_EXTENSIONS = None  # Set to list of extensions like ['.pdf', '.jpg'] or None for all types