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
    
    # Try to get from Snowflake database secrets using SQL
    try:
        # This will work when running in Snowflake Streamlit
        access_key = st.session_state.get('aws_access_key')
        secret_key = st.session_state.get('aws_secret_key')
        region = st.session_state.get('aws_region')
        bucket_name = st.session_state.get('aws_bucket_name')
        
        if not access_key:
            # Try to fetch from Snowflake secrets using SQL
            conn = st.connection("snowflake")
            access_key_result = conn.query("SELECT SYSTEM$GET_SECRET_STRING('aws_access_key_id') as secret_value")
            secret_key_result = conn.query("SELECT SYSTEM$GET_SECRET_STRING('aws_secret_access_key') as secret_value")
            region_result = conn.query("SELECT SYSTEM$GET_SECRET_STRING('aws_region') as secret_value")
            bucket_result = conn.query("SELECT SYSTEM$GET_SECRET_STRING('s3_bucket_name') as secret_value")
            
            if not access_key_result.empty:
                access_key = access_key_result.iloc[0]['SECRET_VALUE']
                secret_key = secret_key_result.iloc[0]['SECRET_VALUE']
                region = region_result.iloc[0]['SECRET_VALUE']
                bucket_name = bucket_result.iloc[0]['SECRET_VALUE']
                
                # Cache in session state
                st.session_state.aws_access_key = access_key
                st.session_state.aws_secret_key = secret_key
                st.session_state.aws_region = region
                st.session_state.aws_bucket_name = bucket_name
        
        if access_key and secret_key and bucket_name:
            return {
                'access_key': access_key,
                'secret_key': secret_key,
                'region': region or 'us-west-2',
                'bucket_name': bucket_name
            }
    except Exception as e:
        st.error(f"Error accessing Snowflake secrets: {str(e)}")
    
    # Fallback to environment variables
    return {
        'access_key': os.getenv('AWS_ACCESS_KEY_ID', ''),
        'secret_key': os.getenv('AWS_SECRET_ACCESS_KEY', ''),
        'region': os.getenv('AWS_REGION', 'us-west-2'),
        'bucket_name': os.getenv('S3_BUCKET_NAME', '')
    }

def generate_aws_signature_v4(method, region, service, access_key, secret_key, url, headers=None, payload=''):
    """Generate AWS Signature Version 4 for S3 requests"""
    if headers is None:
        headers = {}
    
    # Parse URL
    parsed_url = urllib.parse.urlparse(url)
    host = parsed_url.netloc
    path = parsed_url.path
    query = parsed_url.query
    
    # Create canonical request
    canonical_uri = quote(path, safe='/')
    canonical_querystring = query
    canonical_headers = '\n'.join([f"{k.lower()}:{v}" for k, v in sorted(headers.items())]) + '\n'
    signed_headers = ';'.join([k.lower() for k in sorted(headers.keys())])
    payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    
    canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    
    # Create string to sign
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    date = timestamp[:8]
    credential_scope = f"{date}/{region}/{service}/aws4_request"
    algorithm = "AWS4-HMAC-SHA256"
    
    string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    
    # Calculate signature
    signing_key = get_signing_key(secret_key, date, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    
    return signature, timestamp, credential_scope

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
    
    :param bucket_name: The name of the S3 bucket.
    :param object_key: The key (path and filename) in the S3 bucket.
    :param access_key: AWS access key ID.
    :param secret_key: AWS secret access key.
    :param region: AWS region.
    :param expires_in: The number of seconds the presigned URL is valid for.
    :return: The presigned URL.
    """
    try:
        # URL encode the object key
        encoded_key = quote(object_key, safe='')
        
        # Create timestamp and expiration
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        date = timestamp[:8]
        expires_timestamp = (datetime.utcnow().timestamp() + expires_in)
        
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