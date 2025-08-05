import streamlit as st
import requests
import uuid
from datetime import datetime
import os
import json
import hashlib
import hmac
import urllib.parse
from urllib.parse import quote

# AWS Configuration - Replace with your values
# For local development, create config_local.py with your actual credentials
try:
    from config_local import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME
except ImportError:
    # Fallback values - replace these with your actual values or use environment variables
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "YOUR_AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "YOUR_AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-bucket-name")

def get_aws_credentials():
    """
    Get AWS credentials with simplified approach.
    Priority: Session state > Config/Environment constants > Manual input
    """
    # First, check if credentials are already in session state (from manual input)
    access_key = st.session_state.get('aws_access_key')
    secret_key = st.session_state.get('aws_secret_key')
    region = st.session_state.get('aws_region', AWS_REGION)
    bucket_name = st.session_state.get('aws_bucket_name')
    
    if access_key and secret_key and bucket_name:
        return {
            'access_key': access_key,
            'secret_key': secret_key,
            'region': region,
            'bucket_name': bucket_name
        }
    
    # Try to use configured constants (from config_local.py or environment)
    if (AWS_ACCESS_KEY_ID != "YOUR_AWS_ACCESS_KEY_ID" and 
        AWS_SECRET_ACCESS_KEY != "YOUR_AWS_SECRET_ACCESS_KEY" and 
        S3_BUCKET_NAME != "your-bucket-name"):
        return {
            'access_key': AWS_ACCESS_KEY_ID,
            'secret_key': AWS_SECRET_ACCESS_KEY,
            'region': AWS_REGION,
            'bucket_name': S3_BUCKET_NAME
        }
    
    # Try environment variables (local development fallback)
    env_creds = {
        'access_key': os.getenv('AWS_ACCESS_KEY_ID', ''),
        'secret_key': os.getenv('AWS_SECRET_ACCESS_KEY', ''),
        'region': os.getenv('AWS_REGION', 'us-west-2'),
        'bucket_name': os.getenv('S3_BUCKET_NAME', '')
    }
    
    if all([env_creds['access_key'], env_creds['secret_key'], env_creds['bucket_name']]):
        # Cache in session state
        st.session_state.aws_access_key = env_creds['access_key']
        st.session_state.aws_secret_key = env_creds['secret_key']
        st.session_state.aws_region = env_creds['region']
        st.session_state.aws_bucket_name = env_creds['bucket_name']
        return env_creds
    
    # Return empty credentials (will trigger manual input)
    return {
        'access_key': '',
        'secret_key': '',
        'region': 'us-west-2',
        'bucket_name': ''
    }

def get_signing_key(secret_key, date, region, service):
    """Generate AWS signing key"""
    k_date = hmac.new(f"AWS4{secret_key}".encode('utf-8'), date.encode('utf-8'), hashlib.sha256).digest()
    k_region = hmac.new(k_date, region.encode('utf-8'), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service.encode('utf-8'), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, "aws4_request".encode('utf-8'), hashlib.sha256).digest()
    return k_signing

def generate_presigned_url(bucket_name, object_key, access_key, secret_key, region, expires_in=3600):
    """
    Generate a presigned Amazon S3 URL for PUT operations without boto3.
    """
    try:
        # URL encode the object key
        encoded_key = quote(object_key, safe='')
        
        # Create timestamp and expiration
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        date = timestamp[:8]
        
        # Build the query parameters
        credential = f"{access_key}/{date}/{region}/s3/aws4_request"
        
        query_params = {
            'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
            'X-Amz-Credential': credential,
            'X-Amz-Date': timestamp,
            'X-Amz-Expires': str(expires_in),
            'X-Amz-SignedHeaders': 'host'
        }
        
        # Build the URL
        host = f"{bucket_name}.s3.{region}.amazonaws.com"
        url = f"https://{host}/{encoded_key}"
        
        # Create canonical query string
        canonical_query = '&'.join([f"{k}={quote(str(v), safe='')}" for k, v in sorted(query_params.items())])
        
        # Create canonical request
        canonical_request = f"PUT\n/{encoded_key}\n{canonical_query}\nhost:{host}\n\nhost\nUNSIGNED-PAYLOAD"
        
        # Create string to sign
        credential_scope = f"{date}/{region}/s3/aws4_request"
        string_to_sign = f"AWS4-HMAC-SHA256\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # Calculate signature
        signing_key = get_signing_key(secret_key, date, region, 's3')
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Add signature to query parameters
        query_params['X-Amz-Signature'] = signature
        
        # Build final URL
        final_query = '&'.join([f"{k}={quote(str(v), safe='')}" for k, v in sorted(query_params.items())])
        final_url = f"{url}?{final_query}"
        
        return final_url
        
    except Exception as e:
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
    
    # Get AWS credentials
    creds = get_aws_credentials()
    if not all([creds['access_key'], creds['secret_key'], creds['bucket_name']]):
        st.warning("⚠️ AWS credentials not configured.")
        
        # Manual credential input
        st.subheader("🔑 Enter AWS Credentials")
        
        with st.expander("AWS Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                manual_access_key = st.text_input("AWS Access Key ID", type="password", key="manual_access_key")
                manual_region = st.selectbox("AWS Region", ["us-west-2", "us-east-1", "us-west-1", "eu-west-1", "eu-central-1"], key="manual_region")
            
            with col2:
                manual_secret_key = st.text_input("AWS Secret Access Key", type="password", key="manual_secret_key")
                manual_bucket = st.text_input("S3 Bucket Name", value="mquarfot-dev", key="manual_bucket")
            
            if st.button("Save Credentials", type="primary"):
                if all([manual_access_key, manual_secret_key, manual_bucket]):
                    # Store in session state
                    st.session_state.aws_access_key = manual_access_key
                    st.session_state.aws_secret_key = manual_secret_key
                    st.session_state.aws_region = manual_region
                    st.session_state.aws_bucket_name = manual_bucket
                    st.success("✅ Credentials saved for this session!")
                    st.rerun()
                else:
                    st.error("❌ Please fill in all credential fields")
        
        # Show setup instructions
        with st.expander("📋 Production Setup Instructions"):
            st.markdown("""
            **For Production - Snowflake Secrets (Recommended):**
            ```sql
            CREATE OR REPLACE SECRET aws_access_key_id
            TYPE = GENERIC_STRING
            SECRET_STRING = 'your-access-key-id';
            
            CREATE OR REPLACE SECRET aws_secret_access_key
            TYPE = GENERIC_STRING
            SECRET_STRING = 'your-secret-access-key';
            
            CREATE OR REPLACE SECRET aws_region
            TYPE = GENERIC_STRING
            SECRET_STRING = 'us-west-2';
            
            CREATE OR REPLACE SECRET s3_bucket_name
            TYPE = GENERIC_STRING
            SECRET_STRING = 'your-bucket-name';
            ```
            
            **Grant Permissions:**
            ```sql
            GRANT USAGE ON SECRET aws_access_key_id TO ROLE YOUR_ROLE;
            GRANT USAGE ON SECRET aws_secret_access_key TO ROLE YOUR_ROLE;
            GRANT USAGE ON SECRET aws_region TO ROLE YOUR_ROLE;
            GRANT USAGE ON SECRET s3_bucket_name TO ROLE YOUR_ROLE;
            ```
            """)
        return
    
    # Show current configuration
    st.info(f"✅ Connected to S3 bucket: `{creds['bucket_name']}` in region `{creds['region']}`")
    
    # File upload section
    st.header("Upload Files")
    
    # Check Streamlit version and provide appropriate interface
    streamlit_version = st.__version__
    version_parts = [int(x) for x in streamlit_version.split('.')]
    has_file_uploader = (version_parts[0] > 1) or (version_parts[0] == 1 and version_parts[1] >= 26)
    
    if has_file_uploader:
        # Modern file uploader (Streamlit 1.26+)
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            accept_multiple_files=True,
            help="Select one or more files to upload to S3"
        )
    else:
        # Fallback for older Streamlit versions
        st.info("📁 **File Upload Instructions:**")
        st.markdown(f"""
        Since you're using Streamlit version {streamlit_version} (requires 1.26+), please use the text input method below:
        """)
        
        # Alternative method: text input for file content
        st.subheader("Text Content Upload")
        
        col1, col2 = st.columns(2)
        with col1:
            filename = st.text_input("Enter filename (with extension):", placeholder="example.csv")
        with col2:
            file_path = st.text_input("S3 path (optional):", placeholder="folder/subfolder/")
        
        file_content_text = st.text_area(
            "Paste your file content here:",
            height=200,
            help="Copy and paste the content of your file here"
        )
        
        uploaded_files = None
        
        if st.button("Upload Text Content", type="primary") and filename and file_content_text:
            # Convert text to bytes
            file_content = file_content_text.encode('utf-8')
            
            # Generate file key
            if file_path:
                file_key = f"{file_path.rstrip('/')}/{filename}"
            else:
                unique_filename = generate_unique_filename(filename)
                file_key = f"uploads/{unique_filename}"
            
            # Upload the content
            with st.spinner(f"Uploading {filename}..."):
                credentials = get_aws_credentials()
                presigned_url = generate_presigned_url(
                    credentials['bucket_name'], 
                    file_key,
                    credentials['access_key'],
                    credentials['secret_key'],
                    credentials['region']
                )
                
                if presigned_url:
                    success = upload_file_to_s3(presigned_url, file_content)
                    
                    if success:
                        st.success(f"✅ Successfully uploaded {filename}")
                        st.info(f"📍 File location: s3://{credentials['bucket_name']}/{file_key}")
                    else:
                        st.error(f"❌ Failed to upload {filename}")
        
        # Show upgrade recommendation
        st.markdown("---")
        st.subheader("🔧 For Full File Upload Functionality")
        st.info(f"""
        **Recommended**: Ask your administrator to upgrade Snowflake Streamlit to version 1.26+ 
        to enable drag-and-drop file uploads.
        
        **Current version**: {streamlit_version}  
        **Required version**: 1.26.0+
        """)
        return  # Exit early for older versions
    
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
                                creds['bucket_name'], 
                                file_key,
                                creds['access_key'],
                                creds['secret_key'],
                                creds['region']
                            )
                            
                            if presigned_url:
                                # Upload file
                                file_content = uploaded_file.read()
                                success = upload_file_to_s3(presigned_url, file_content)
                                
                                if success:
                                    st.success(f"✅ Successfully uploaded {uploaded_file.name}")
                                    st.info(f"📍 File location: s3://{creds['bucket_name']}/{file_key}")
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
                    presigned_url = generate_presigned_url(
                        creds['bucket_name'], 
                        file_key,
                        creds['access_key'],
                        creds['secret_key'],
                        creds['region']
                    )
                    
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
        st.info(f"""
        **Storage Details:**
        - Bucket: `{creds['bucket_name']}`
        - Region: `{creds['region']}`
        - Default folder: `uploads/`
        - File naming: `YYYYMMDD_HHMMSS_ID_filename.ext`
        """)

if __name__ == "__main__":
    main()