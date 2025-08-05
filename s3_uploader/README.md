# S3 File Uploader - Streamlit in Snowflake

A Streamlit application that allows customers and clients to securely upload files directly to your S3 bucket using presigned URLs.

## Features

- 🔒 Secure file uploads using AWS S3 presigned URLs
- 📁 Multiple file upload support
- 🎯 Custom file path specification
- 📊 Upload progress tracking
- 🔄 Automatic file naming to prevent conflicts
- 💾 Bulk upload capability
- 📱 Responsive web interface

## Setup Instructions

### 1. Secure Configuration ✅ COMPLETED

Your AWS credentials are now securely configured using environment variables and Snowflake secrets instead of hardcoded values.

**🔒 Security Features:**
- ✅ Credentials removed from source code
- ✅ `.gitignore` configured to prevent credential commits
- ✅ Support for Snowflake secrets (production)
- ✅ Support for environment variables (local development)
- ✅ Automatic fallback between credential sources

### 2. Configure Credentials

**For Snowflake Production (Recommended):**
1. Run the setup script: `setup_snowflake_secrets.sql`
2. This creates secure Snowflake secrets for your AWS credentials

**For Local Development:**
1. Copy `env_template` to `.env`
2. The app will automatically load credentials from the `.env` file

### 3. Deploy to Snowflake

1. **Set up Snowflake secrets first:**
   ```sql
   -- Run the commands in setup_snowflake_secrets.sql
   ```

2. **Upload files to Snowflake Stage:**
   ```sql
   -- Create a stage for your Streamlit app
   CREATE STAGE IF NOT EXISTS streamlit_stage;
   
   -- Upload the files
   PUT file://streamlit_app.py @streamlit_stage;
   PUT file://requirements.txt @streamlit_stage;
   ```

3. **Create the Streamlit App in Snowflake:**
   ```sql
   CREATE STREAMLIT s3_file_uploader
   ROOT_LOCATION = '@streamlit_stage'
   MAIN_FILE = 'streamlit_app.py'
   QUERY_WAREHOUSE = 'YOUR_WAREHOUSE_NAME';
   ```

4. **Grant permissions (as ACCOUNTADMIN):**
   ```sql
   GRANT USAGE ON STREAMLIT s3_file_uploader TO ROLE your_role;
   GRANT USAGE ON SECRET aws_access_key_id TO ROLE your_role;
   GRANT USAGE ON SECRET aws_secret_access_key TO ROLE your_role;
   GRANT USAGE ON SECRET aws_region TO ROLE your_role;
   GRANT USAGE ON SECRET s3_bucket_name TO ROLE your_role;
   ```

### 4. Local Development (Optional)

For local testing before deploying to Snowflake:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app locally
streamlit run streamlit_app.py
```

## AWS S3 Bucket Permissions

Your S3 bucket should have a policy that allows the AWS user to generate presigned URLs. Example policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": "arn:aws:s3:::mquarfot-dev/*"
        }
    ]
}
```

## Security Considerations

- ✅ Uses presigned URLs for secure, time-limited access
- ✅ No AWS credentials stored client-side
- ✅ Files are uploaded directly to S3 (not through your server)
- ✅ Automatic unique naming prevents file conflicts
- ⚠️ Configure appropriate bucket policies and CORS if needed

## File Organization

Uploaded files are automatically organized with timestamps and unique IDs:
- Pattern: `uploads/YYYYMMDD_HHMMSS_ID_filename.ext`
- Example: `uploads/20241201_143052_a1b2c3d4_document.pdf`

## Usage

1. Navigate to your Streamlit app in Snowflake
2. Select one or more files to upload
3. Optionally specify custom file paths
4. Click "Upload" for individual files or "Upload All Files" for bulk uploads
5. Monitor upload progress and confirmation messages

## Troubleshooting

- **"AWS configuration error"**: Check your AWS credentials and region
- **"Upload failed"**: Verify S3 bucket permissions and network connectivity
- **"File too large"**: Check your bucket's maximum object size limits
- **CORS errors**: Configure CORS policy on your S3 bucket if accessing from browser

## Support

Contact your system administrator for:
- AWS credential configuration
- S3 bucket access issues
- Snowflake deployment assistance