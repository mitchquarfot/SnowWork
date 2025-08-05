-- Snowflake Secrets Setup for S3 File Uploader
-- Run these commands as ACCOUNTADMIN or user with appropriate privileges

-- Option 1: Create individual secrets (recommended)
CREATE OR REPLACE SECRET aws_access_key_id
TYPE = GENERIC_STRING
SECRET_STRING = 'YOUR_AWS_ACCESS_KEY_ID';

CREATE OR REPLACE SECRET aws_secret_access_key
TYPE = GENERIC_STRING
SECRET_STRING = 'YOUR_AWS_SECRET_ACCESS_KEY';

CREATE OR REPLACE SECRET aws_region
TYPE = GENERIC_STRING
SECRET_STRING = 'us-west-2';

CREATE OR REPLACE SECRET s3_bucket_name
TYPE = GENERIC_STRING
SECRET_STRING = 'your-bucket-name';

-- Option 2: Create a single JSON secret (alternative)
CREATE OR REPLACE SECRET aws_credentials
TYPE = GENERIC_STRING
SECRET_STRING = '{
    "access_key_id": "YOUR_AWS_ACCESS_KEY_ID",
    "secret_access_key": "YOUR_AWS_SECRET_ACCESS_KEY",
    "region": "us-west-2",
    "bucket_name": "your-bucket-name"
}';

-- Grant usage on secrets to appropriate roles
GRANT USAGE ON SECRET aws_access_key_id TO ROLE SYSADMIN;
GRANT USAGE ON SECRET aws_secret_access_key TO ROLE SYSADMIN;
GRANT USAGE ON SECRET aws_region TO ROLE SYSADMIN;
GRANT USAGE ON SECRET s3_bucket_name TO ROLE SYSADMIN;
GRANT USAGE ON SECRET aws_credentials TO ROLE SYSADMIN;

-- Verify secrets were created
SHOW SECRETS LIKE 'aws%';

-- To view a secret (for testing only)
-- SELECT GET_SECRET_STRING('aws_access_key_id');