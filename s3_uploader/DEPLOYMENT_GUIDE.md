# S3 File Uploader - Isolated Snowflake Deployment Guide

This guide will help you deploy the S3 File Uploader in a completely isolated environment for client access.

## 🎯 **Deployment Goals**

- ✅ Isolated infrastructure (warehouse, database, schema)
- ✅ Dedicated client role with minimal permissions
- ✅ Cost control and monitoring
- ✅ No access to other Snowflake objects
- ✅ Easy client user management

## 📋 **Pre-Deployment Checklist**

- [ ] You have ACCOUNTADMIN role access
- [ ] Your working Streamlit app files are ready
- [ ] You have your AWS credentials configured in the app
- [ ] You've tested the app locally (confirmed uploads work)

## 🚀 **Deployment Steps**

### **Step 1: Create Isolated Infrastructure**

Run the entire `snowflake_deployment_isolated.sql` script in Snowflake:

```sql
-- Run this file in Snowflake SQL Worksheet
-- File: snowflake_deployment_isolated.sql
```

This creates:
- **Warehouse**: `S3_UPLOADER_WH` (XSMALL, auto-suspend)
- **Database**: `S3_UPLOADER_DB`
- **Schema**: `CLIENT_ACCESS`
- **Stage**: `S3_UPLOADER_STAGE`
- **Role**: `S3_UPLOADER_CLIENT_ROLE`
- **Resource Monitor**: `S3_UPLOADER_MONITOR` (10 credits/month)

### **Step 2: Upload Streamlit Files**

After running the infrastructure script, upload your app files:

```sql
-- Upload the working Streamlit app
PUT file:///Users/mquarfot/Desktop/SnowWork/s3_uploader/streamlit_app.py @S3_UPLOADER_DB.CLIENT_ACCESS.S3_UPLOADER_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

PUT file:///Users/mquarfot/Desktop/SnowWork/s3_uploader/requirements.txt @S3_UPLOADER_DB.CLIENT_ACCESS.S3_UPLOADER_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Verify upload
LIST @S3_UPLOADER_DB.CLIENT_ACCESS.S3_UPLOADER_STAGE;
```

### **Step 3: Get Streamlit App URL**

```sql
-- Get the app URL for clients
SHOW STREAMLITS LIKE 'S3_FILE_UPLOADER_APP' IN SCHEMA S3_UPLOADER_DB.CLIENT_ACCESS;
```

**Note the URL** - this is what you'll share with clients.

### **Step 4: Create Client Users**

Edit and run `client_user_management.sql`:

1. **Customize the user templates** with real client information
2. **Set secure passwords** (users must change on first login)
3. **Add client email addresses** for notifications
4. **Set expiration dates** if needed

Example:
```sql
CREATE OR REPLACE USER ACME_CORP_USER
    PASSWORD = 'TempSecure123!'
    DEFAULT_ROLE = 'S3_UPLOADER_CLIENT_ROLE'
    DEFAULT_WAREHOUSE = 'S3_UPLOADER_WH'
    DEFAULT_NAMESPACE = 'S3_UPLOADER_DB.CLIENT_ACCESS'
    MUST_CHANGE_PASSWORD = TRUE
    EMAIL = 'uploads@acmecorp.com'
    DISPLAY_NAME = 'ACME Corp - File Upload User'
    COMMENT = 'File upload access for ACME Corporation';

GRANT ROLE S3_UPLOADER_CLIENT_ROLE TO USER ACME_CORP_USER;
```

### **Step 5: Test Client Access**

1. **Login as client user** to Snowflake
2. **Navigate to the Streamlit app URL**
3. **Test file upload functionality**
4. **Verify files appear in your S3 bucket**

## 🔐 **Security Features**

### **Isolation**
- Clients can ONLY access the S3 uploader app
- No visibility into other databases, warehouses, or objects
- Dedicated role with minimal permissions

### **Cost Control**
- Small warehouse (XSMALL) with auto-suspend
- Resource monitor with 10 credit monthly limit
- Automatic suspension at 100% quota

### **Access Control**
- Time-limited user accounts (optional)
- Password change required on first login
- Network policies (optional - configure in script)

### **Monitoring**
- User activity tracking
- Warehouse usage monitoring  
- Login attempt logging
- Cost tracking

## 📊 **Client Information to Share**

Provide clients with:

```
Snowflake Account: [YOUR_ACCOUNT_IDENTIFIER]
Username: [CLIENT_USERNAME]
Password: [TEMPORARY_PASSWORD]
App URL: [STREAMLIT_APP_URL]

Instructions:
1. Login to Snowflake with provided credentials
2. Change password when prompted
3. Navigate to the app URL
4. Upload files as needed
```

## 🔧 **Management Commands**

### **Monitor Usage**
```sql
-- Check recent client activity
SELECT USER_NAME, START_TIME, QUERY_TEXT 
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY 
WHERE ROLE_NAME = 'S3_UPLOADER_CLIENT_ROLE'
ORDER BY START_TIME DESC;

-- Check warehouse costs
SELECT WAREHOUSE_NAME, CREDITS_USED, START_TIME
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY 
WHERE WAREHOUSE_NAME = 'S3_UPLOADER_WH'
ORDER BY START_TIME DESC;
```

### **User Management**
```sql
-- Disable user
ALTER USER CLIENT_USER SET DISABLED = TRUE;

-- Reset password
ALTER USER CLIENT_USER SET PASSWORD = 'NewTemp123!' MUST_CHANGE_PASSWORD = TRUE;

-- Extend access
ALTER USER CLIENT_USER SET DAYS_TO_EXPIRY = 180;
```

### **Emergency Shutdown**
```sql
-- Suspend warehouse (stops all client access)
ALTER WAREHOUSE S3_UPLOADER_WH SUSPEND;

-- Disable all client users
-- (Use client_user_management.sql for bulk operations)
```

## 🏗️ **Infrastructure Summary**

| Object | Name | Purpose |
|--------|------|---------|
| Warehouse | `S3_UPLOADER_WH` | Compute for Streamlit app |
| Database | `S3_UPLOADER_DB` | Container for app objects |
| Schema | `CLIENT_ACCESS` | Namespace for client access |
| Stage | `S3_UPLOADER_STAGE` | Streamlit app files |
| Role | `S3_UPLOADER_CLIENT_ROLE` | Client permissions |
| App | `S3_FILE_UPLOADER_APP` | The Streamlit application |
| Monitor | `S3_UPLOADER_MONITOR` | Cost control |

## 🆘 **Troubleshooting**

### **App Won't Load**
- Check warehouse is not suspended
- Verify user has correct role
- Confirm app URL is correct

### **Upload Fails**
- Check AWS credentials in app
- Verify S3 bucket permissions
- Test with smaller file

### **Access Denied**
- Confirm user has `S3_UPLOADER_CLIENT_ROLE`
- Check role grants
- Verify user is not disabled

### **High Costs**
- Check resource monitor settings
- Review warehouse size (XSMALL recommended)
- Monitor concurrent usage

## 🎉 **Success Criteria**

✅ Client can login with provided credentials  
✅ Client can access Streamlit app URL  
✅ Client can upload files successfully  
✅ Files appear in your S3 bucket  
✅ Client cannot access other Snowflake objects  
✅ Costs remain within expected limits  

Your S3 File Uploader is now ready for client use! 🚀