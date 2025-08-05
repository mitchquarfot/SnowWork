import streamlit as st
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import requests
import uuid
from datetime import datetime
import os

# Load environment variables from .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, skip loading
    pass

def get_aws_credentials():
    """
    Get AWS credentials from Snowflake secrets or environment variables.
    Priority: Snowflake secrets > Environment variables > Default values
    """
    try:
        # Try to get from Snowflake secrets first (recommended for production)
        if hasattr(st, 'secrets') and 'aws' in st.secrets:
            return {
                'access_key': st.secrets.aws.access_key_id,
                'secret_key': st.secrets.aws.secret_access_key,
                'region': st.secrets.aws.region,
                'bucket_name': st.secrets.aws.bucket_name
            }
    except Exception:
        pass
    
    # Fallback to environment variables
    return {
        'access_key': os.getenv('AWS_ACCESS_KEY_ID', ''),
        'secret_key': os.getenv('AWS_SECRET_ACCESS_KEY', ''),
        'region': os.getenv('AWS_REGION', 'us-west-2'),
        'bucket_name': os.getenv('S3_BUCKET_NAME', '')
    }

def init_s3_client():
    """Initialize S3 client with credentials"""
    try:
        creds = get_aws_credentials()
        
        if not all([creds['access_key'], creds['secret_key'], creds['bucket_name']]):
            st.error("⚠️ AWS credentials not found. Please configure Snowflake secrets or environment variables.")
            return None, None
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=creds['access_key'],
            aws_secret_access_key=creds['secret_key'],
            region_name=creds['region']
        )
        return s3_client, creds['bucket_name']
    except Exception as e:
        st.error(f"Failed to initialize S3 client: {str(e)}")
        return None, None

def generate_presigned_url(s3_client, bucket_name, object_key, expires_in=3600):
    """
    Generate a presigned Amazon S3 URL for PUT operations.
    
    :param s3_client: A Boto3 Amazon S3 client.
    :param bucket_name: The name of the S3 bucket.
    :param object_key: The key (path and filename) in the S3 bucket.
    :param expires_in: The number of seconds the presigned URL is valid for.
    :return: The presigned URL.
    """
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key,
                'ContentType': 'application/octet-stream'
            },
            ExpiresIn=expires_in
        )
        return url
    except ClientError as e:
        st.error(f"Couldn't generate presigned URL: {str(e)}")
        return None

def upload_file_to_s3(presigned_url, file_content):
    """Upload file content to S3 using presigned URL"""
    try:
        response = requests.put(
            presigned_url,
            data=file_content,
            headers={'Content-Type': 'application/octet-stream'}
        )
        return response.status_code == 200
    except Exception as e:
        st.error(f"Upload failed: {str(e)}")
        return False

def generate_unique_filename(original_filename):
    """Generate a unique filename to prevent conflicts"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    name, ext = os.path.splitext(original_filename)
    return f"{timestamp}_{unique_id}_{name}{ext}"

def main():
    st.set_page_config(
        page_title="S3 File Uploader",
        page_icon="📁",
        layout="wide"
    )
    
    st.title("📁 S3 File Uploader")
    st.markdown("Upload your files securely to our S3 storage")
    
    # Initialize S3 client and get credentials
    s3_client, bucket_name = init_s3_client()
    if not s3_client or not bucket_name:
        st.info("📋 **Setup Instructions:**")
        st.markdown("""
        **Option 1: Snowflake Secrets (Recommended for Production)**
        ```sql
        CREATE SECRET aws_credentials
        TYPE = GENERIC
        SECRET_STRING = '{
            "access_key_id": "your-access-key",
            "secret_access_key": "your-secret-key",
            "region": "us-west-2",
            "bucket_name": "your-bucket-name"
        }';
        ```
        
        **Option 2: Environment Variables (Local Development)**
        Set these environment variables before running the app:
        - `AWS_ACCESS_KEY_ID`
        - `AWS_SECRET_ACCESS_KEY`
        - `AWS_REGION`
        - `S3_BUCKET_NAME`
        """)
        return
    
    # File upload section
    st.header("Upload Files")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        accept_multiple_files=True,
        help="Select one or more files to upload to S3"
    )
    
    if uploaded_files:
        st.subheader("Files to Upload:")
        
        # Display selected files
        for i, uploaded_file in enumerate(uploaded_files):
            with st.expander(f"📄 {uploaded_file.name} ({uploaded_file.size:,} bytes)"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Option to customize the file path
                    custom_path = st.text_input(
                        "Custom file path (optional)",
                        value="",
                        key=f"path_{i}",
                        help="Leave empty for automatic naming, or specify a custom path like 'folder/subfolder/filename.ext'"
                    )
                
                with col2:
                    if st.button(f"Upload", key=f"upload_{i}"):
                        # Generate file key
                        if custom_path:
                            file_key = custom_path
                        else:
                            unique_filename = generate_unique_filename(uploaded_file.name)
                            file_key = f"uploads/{unique_filename}"
                        
                        # Show upload progress
                        with st.spinner(f"Uploading {uploaded_file.name}..."):
                            # Generate presigned URL
                            presigned_url = generate_presigned_url(
                                s3_client, 
                                bucket_name, 
                                file_key
                            )
                            
                            if presigned_url:
                                # Upload file
                                file_content = uploaded_file.read()
                                success = upload_file_to_s3(presigned_url, file_content)
                                
                                if success:
                                    st.success(f"✅ Successfully uploaded {uploaded_file.name}")
                                    st.info(f"📍 File location: s3://{bucket_name}/{file_key}")
                                else:
                                    st.error(f"❌ Failed to upload {uploaded_file.name}")
        
        # Bulk upload option
        st.markdown("---")
        if len(uploaded_files) > 1:
            if st.button("🚀 Upload All Files", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                successful_uploads = 0
                total_files = len(uploaded_files)
                
                for i, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Uploading {uploaded_file.name}...")
                    
                    # Generate unique filename
                    unique_filename = generate_unique_filename(uploaded_file.name)
                    file_key = f"uploads/{unique_filename}"
                    
                    # Generate presigned URL and upload
                    presigned_url = generate_presigned_url(s3_client, bucket_name, file_key)
                    
                    if presigned_url:
                        file_content = uploaded_file.read()
                        if upload_file_to_s3(presigned_url, file_content):
                            successful_uploads += 1
                    
                    # Update progress
                    progress_bar.progress((i + 1) / total_files)
                
                status_text.text("")
                progress_bar.empty()
                
                if successful_uploads == total_files:
                    st.success(f"🎉 Successfully uploaded all {total_files} files!")
                else:
                    st.warning(f"⚠️ Uploaded {successful_uploads} out of {total_files} files")
    
    # Information section
    st.markdown("---")
    st.subheader("ℹ️ Upload Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **File Upload Guidelines:**
        - Maximum file size: Check with your administrator
        - Supported formats: All file types
        - Files are automatically renamed to prevent conflicts
        - Uploads are secure and encrypted
        """)
    
    with col2:
        creds = get_aws_credentials()
        st.info(f"""
        **Storage Details:**
        - Bucket: `{bucket_name}`
        - Region: `{creds['region']}`
        - Default folder: `uploads/`
        - File naming: `YYYYMMDD_HHMMSS_ID_filename.ext`
        """)

if __name__ == "__main__":
    main()