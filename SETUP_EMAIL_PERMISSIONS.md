# Setting Up Email Attachment Indexing

This application can index email attachments from all Office 365 mailboxes. This requires additional Azure AD permissions.

## Required Azure AD Permissions

### Application Permissions (Admin Consent Required)

You need to add the following **Application** permissions to your Azure AD App Registration:

1. **User.Read.All** (Application permission)
   - Allows the app to read all users' basic profiles
   - **REQUIRED** to list all users in the organization
   - Without this, you'll get "403 Forbidden" when trying to fetch users

2. **Mail.Read** (Application permission)
   - Allows the app to read mail in all mailboxes without a signed-in user
   - Required to fetch emails with attachments

### Steps to Add Email Permissions

1. Go to **Azure Portal** → **Azure Active Directory** → **App registrations**
2. Select your app registration
3. Go to **"API permissions"** in the left menu
4. Click **"Add a permission"**
5. Select **"Microsoft Graph"**
6. Select **"Application permissions"** (not Delegated)
7. Search for and add **BOTH** permissions:
   - **User.Read.All** - To list all users
   - **Mail.Read** - To read emails from mailboxes
8. Click **"Add permissions"** after selecting each one
9. **CRITICAL**: Click **"Grant admin consent for [Your Organization]"** to grant consent
   - This is required for application permissions to work
   - Only administrators can grant consent
   - You must grant consent for BOTH permissions

### Verify Permissions

After adding permissions, you should see:
- **User.Read.All** (Application) - Status: ✅ Granted for [Your Organization]
- **Mail.Read** (Application) - Status: ✅ Granted for [Your Organization]

**If you see "403 Forbidden" errors in logs:**
- This means one or both permissions are missing or not granted
- Check that both permissions are listed and show "Granted" status

## How It Works

1. **Automatic Indexing**: When you click "Index Selected Sites", the application will:
   - First index all selected SharePoint sites
   - Then automatically index email attachments from all mailboxes

2. **What Gets Indexed**:
   - Only emails that have attachments
   - Only attachment metadata (name, size, type, dates, sender)
   - **No email content is indexed**
   - **No attachments are downloaded** - only links to view the email in Outlook

3. **Email Attachment Display**:
   - Email attachments appear in the same file list as SharePoint files
   - They are marked with source "Email" in the path column
   - Clicking the link opens the email in Outlook Web App

4. **Search**: Email attachments are searchable alongside SharePoint files

## Notes

- **Performance**: Indexing all mailboxes can take time, especially with many users
- **Incremental Updates**: Subsequent indexing only fetches new/modified emails
- **Privacy**: Only attachment metadata is indexed, not email content
- **Permissions**: The app needs Mail.Read application permission to access all mailboxes

## Troubleshooting

### "403 Forbidden" or "Insufficient privileges" error

**If you see "403 Forbidden" when fetching users:**
- **User.Read.All** application permission is missing or not granted
- Add **User.Read.All** (Application permission)
- Grant admin consent

**If you see "403 Forbidden" when fetching emails:**
- **Mail.Read** application permission is missing or not granted
- Add **Mail.Read** (Application permission)
- Grant admin consent

**General troubleshooting:**
- Ensure **BOTH** permissions are added: User.Read.All AND Mail.Read
- Ensure admin consent is granted for BOTH
- Wait a few minutes after granting consent for permissions to propagate
- Restart the application after adding permissions

### No email attachments found
- Check that users have emails with attachments
- Verify the app has Mail.Read permission
- Check application logs for errors

### Slow indexing
- Email indexing happens after SharePoint indexing
- Large organizations may take significant time
- Progress is shown in the status updates

