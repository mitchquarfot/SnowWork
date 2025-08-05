-- S3 File Uploader - Snowflake Deployment Script
-- Replace YOUR_WAREHOUSE_NAME with your actual warehouse name

-- Step 1: Create a stage for the Streamlit app
CREATE STAGE IF NOT EXISTS s3_uploader_stage
COMMENT = 'Stage for S3 File Uploader Streamlit application';

-- Step 2: Upload files to the stage (run these commands in SnowSQL or similar)
-- PUT file:///Users/mquarfot/Desktop/SnowWork/s3_uploader/streamlit_app.py @s3_uploader_stage AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
-- PUT file:///Users/mquarfot/Desktop/SnowWork/s3_uploader/requirements.txt @s3_uploader_stage AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Step 3: Create the Streamlit app
CREATE OR REPLACE STREAMLIT s3_file_uploader
ROOT_LOCATION = '@s3_uploader_stage'
MAIN_FILE = 'streamlit_app.py'
QUERY_WAREHOUSE = 'YOUR_WAREHOUSE_NAME'  -- Replace with your warehouse name
COMMENT = 'S3 File Uploader application for secure file uploads';

-- Step 4: Grant permissions (adjust roles as needed)
-- GRANT USAGE ON STREAMLIT s3_file_uploader TO ROLE PUBLIC;
-- GRANT USAGE ON STREAMLIT s3_file_uploader TO ROLE SYSADMIN;

-- Step 5: Show the Streamlit app URL
SHOW STREAMLITS LIKE 's3_file_uploader';

-- Step 6: Get the app URL (example)
-- The URL will be something like: https://app.snowflake.com/account/streamlit/S3_FILE_UPLOADER