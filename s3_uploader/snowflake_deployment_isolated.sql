-- ================================================================
-- S3 File Uploader - Isolated Snowflake Deployment
-- Creates dedicated infrastructure for client access
-- ================================================================

-- Switch to ACCOUNTADMIN for setup
USE ROLE ACCOUNTADMIN;

-- ================================================================
-- STEP 1: Create Dedicated Warehouse
-- ================================================================

CREATE OR REPLACE WAREHOUSE S3_UPLOADER_WH 
WITH 
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Dedicated warehouse for S3 File Uploader Streamlit app';

-- ================================================================
-- STEP 2: Create Dedicated Database and Schema
-- ================================================================

CREATE OR REPLACE DATABASE S3_UPLOADER_DB
    COMMENT = 'Database for S3 File Uploader application';

USE DATABASE S3_UPLOADER_DB;

CREATE OR REPLACE SCHEMA CLIENT_ACCESS
    COMMENT = 'Schema for client file upload functionality';

USE SCHEMA S3_UPLOADER_DB.CLIENT_ACCESS;

-- ================================================================
-- STEP 3: Create Dedicated Stage for Streamlit Files
-- ================================================================

CREATE OR REPLACE STAGE S3_UPLOADER_STAGE
    COMMENT = 'Stage for S3 File Uploader Streamlit application files';

-- ================================================================
-- STEP 4: Create Client Access Role
-- ================================================================

CREATE OR REPLACE ROLE S3_UPLOADER_CLIENT_ROLE
    COMMENT = 'Role for clients to access S3 File Uploader app only';

-- ================================================================
-- STEP 5: Grant Permissions to Client Role
-- ================================================================

-- Warehouse permissions
GRANT USAGE ON WAREHOUSE S3_UPLOADER_WH TO ROLE S3_UPLOADER_CLIENT_ROLE;

-- Database and schema permissions
GRANT USAGE ON DATABASE S3_UPLOADER_DB TO ROLE S3_UPLOADER_CLIENT_ROLE;
GRANT USAGE ON SCHEMA S3_UPLOADER_DB.CLIENT_ACCESS TO ROLE S3_UPLOADER_CLIENT_ROLE;

-- Stage permissions (for Streamlit app)
GRANT USAGE ON STAGE S3_UPLOADER_DB.CLIENT_ACCESS.S3_UPLOADER_STAGE TO ROLE S3_UPLOADER_CLIENT_ROLE;

-- ================================================================
-- STEP 6: Upload Streamlit Files to Stage
-- ================================================================

-- Run these PUT commands to upload your files:
-- PUT file:///Users/mquarfot/Desktop/SnowWork/s3_uploader/streamlit_app.py @S3_UPLOADER_DB.CLIENT_ACCESS.S3_UPLOADER_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
-- PUT file:///Users/mquarfot/Desktop/SnowWork/s3_uploader/requirements.txt @S3_UPLOADER_DB.CLIENT_ACCESS.S3_UPLOADER_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Verify upload (uncomment after running PUT commands)
-- LIST @S3_UPLOADER_DB.CLIENT_ACCESS.S3_UPLOADER_STAGE;

-- ================================================================
-- STEP 7: Create Streamlit App
-- ================================================================

CREATE OR REPLACE STREAMLIT S3_UPLOADER_DB.CLIENT_ACCESS.S3_FILE_UPLOADER_APP
    ROOT_LOCATION = '@S3_UPLOADER_DB.CLIENT_ACCESS.S3_UPLOADER_STAGE'
    MAIN_FILE = 'streamlit_app.py'
    QUERY_WAREHOUSE = 'S3_UPLOADER_WH'
    COMMENT = 'S3 File Uploader application for client use';

-- ================================================================
-- STEP 8: Grant Streamlit App Access to Client Role
-- ================================================================

GRANT USAGE ON STREAMLIT S3_UPLOADER_DB.CLIENT_ACCESS.S3_FILE_UPLOADER_APP TO ROLE S3_UPLOADER_CLIENT_ROLE;

-- ================================================================
-- STEP 9: Create Client Users (Template)
-- ================================================================

-- Template for creating client users - customize as needed
-- CREATE OR REPLACE USER CLIENT_USER_1
--     PASSWORD = 'TempPassword123!'
--     DEFAULT_ROLE = 'S3_UPLOADER_CLIENT_ROLE'
--     DEFAULT_WAREHOUSE = 'S3_UPLOADER_WH'
--     DEFAULT_NAMESPACE = 'S3_UPLOADER_DB.CLIENT_ACCESS'
--     MUST_CHANGE_PASSWORD = TRUE
--     COMMENT = 'Client user for S3 file uploads';

-- Grant the client role to the user
-- GRANT ROLE S3_UPLOADER_CLIENT_ROLE TO USER CLIENT_USER_1;

-- ================================================================
-- STEP 10: Additional Security (Optional)
-- ================================================================

-- Create network policy for client IP restrictions (optional)
-- CREATE OR REPLACE NETWORK POLICY S3_UPLOADER_CLIENT_POLICY
--     ALLOWED_IP_LIST = ('192.168.1.0/24', '10.0.0.0/8')  -- Replace with client IPs
--     COMMENT = 'Network policy for S3 uploader client access';

-- Apply network policy to client role (optional)
-- ALTER ROLE S3_UPLOADER_CLIENT_ROLE SET NETWORK_POLICY = 'S3_UPLOADER_CLIENT_POLICY';

-- ================================================================
-- STEP 11: Verification and Information
-- ================================================================

-- Show created objects
SHOW WAREHOUSES LIKE 'S3_UPLOADER_WH';
SHOW DATABASES LIKE 'S3_UPLOADER_DB';
SHOW SCHEMAS IN DATABASE S3_UPLOADER_DB;
SHOW STAGES IN SCHEMA S3_UPLOADER_DB.CLIENT_ACCESS;
SHOW STREAMLITS IN SCHEMA S3_UPLOADER_DB.CLIENT_ACCESS;
SHOW ROLES LIKE 'S3_UPLOADER_CLIENT_ROLE';

-- Get Streamlit app URL
SHOW STREAMLITS LIKE 'S3_FILE_UPLOADER_APP' IN SCHEMA S3_UPLOADER_DB.CLIENT_ACCESS;

-- ================================================================
-- STEP 12: Resource Monitoring (Optional)
-- ================================================================

-- Create resource monitor to control costs
CREATE OR REPLACE RESOURCE MONITOR S3_UPLOADER_MONITOR 
WITH 
    CREDIT_QUOTA = 10  -- Adjust as needed
    FREQUENCY = MONTHLY
    START_TIMESTAMP = IMMEDIATELY
    TRIGGERS 
        ON 75 PERCENT DO NOTIFY
        ON 90 PERCENT DO SUSPEND
        ON 100 PERCENT DO SUSPEND_IMMEDIATE;

-- Apply resource monitor to warehouse
ALTER WAREHOUSE S3_UPLOADER_WH SET RESOURCE_MONITOR = 'S3_UPLOADER_MONITOR';

-- ================================================================
-- FINAL NOTES:
-- ================================================================

/*
IMPORTANT: After running this script:

1. Run the PUT commands to upload your Streamlit files
2. Uncomment and customize the client user creation section
3. Note the Streamlit app URL from SHOW STREAMLITS command
4. Test access with a client user account
5. Adjust resource limits and network policies as needed

CLIENT ACCESS SUMMARY:
- Warehouse: S3_UPLOADER_WH
- Database: S3_UPLOADER_DB
- Schema: CLIENT_ACCESS
- Role: S3_UPLOADER_CLIENT_ROLE
- App: S3_FILE_UPLOADER_APP

SECURITY FEATURES:
- Isolated warehouse (cost control)
- Isolated database and schema
- Dedicated role with minimal permissions
- Resource monitoring
- Optional network policies
- No access to other account objects
*/