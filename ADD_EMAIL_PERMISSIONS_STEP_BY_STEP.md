# Step-by-Step: Add Email Permissions in Azure Portal

## ⚠️ Current Error
You're seeing: **"403 Forbidden"** when trying to fetch users. This means **User.Read.All** permission is missing.

## ✅ What You Need to Do

Add **TWO** application permissions in Azure AD:
1. **User.Read.All** (Application)
2. **Mail.Read** (Application)

Then **grant admin consent** for both.

---

## 📋 Detailed Steps

### Step 1: Open Azure Portal

1. Go to: https://portal.azure.com
2. Sign in with your admin account
3. Search for **"Azure Active Directory"** in the top search bar
4. Click on **"Azure Active Directory"**

### Step 2: Navigate to App Registrations

1. In the left menu, click **"App registrations"**
2. Find and click on your app registration (the one you created for SharePoint)
   - It should show your **Client ID** or **Application (client) ID**

### Step 3: Go to API Permissions

1. In the left menu of your app, click **"API permissions"**
2. You should see a list of existing permissions

### Step 4: Add User.Read.All Permission

1. Click the **"Add a permission"** button (usually at the top)
2. A panel opens on the right
3. Click **"Microsoft Graph"**
4. Click **"Application permissions"** (NOT "Delegated permissions")
5. In the search box, type: **"User.Read.All"**
6. Find **"User.Read.All"** in the list
7. **Check the box** next to it
8. Click **"Add permissions"** button at the bottom
9. The panel will close

### Step 5: Add Mail.Read Permission

1. Click **"Add a permission"** again
2. Click **"Microsoft Graph"**
3. Click **"Application permissions"** (NOT "Delegated permissions")
4. In the search box, type: **"Mail.Read"**
5. Find **"Mail.Read"** in the list
6. **Check the box** next to it
7. Click **"Add permissions"** button at the bottom
8. The panel will close

### Step 6: Verify Permissions Are Added

You should now see in the permissions list:
- **User.Read.All** (Application) - Status: ⚠️ **Not granted**
- **Mail.Read** (Application) - Status: ⚠️ **Not granted**

### Step 7: Grant Admin Consent (CRITICAL!)

**This is the most important step! Without this, permissions won't work.**

1. Look for a button that says: **"Grant admin consent for [Your Organization Name]"**
   - It's usually at the top of the permissions list
   - It might be a blue button or a link
2. Click it
3. A confirmation dialog may appear - click **"Yes"** or **"Grant"**
4. Wait for the page to refresh
5. Check the status - it should now show:
   - **User.Read.All** (Application) - Status: ✅ **Granted for [Your Organization]**
   - **Mail.Read** (Application) - Status: ✅ **Granted for [Your Organization]**

### Step 8: Wait and Restart

1. **Wait 2-3 minutes** for permissions to propagate through Microsoft's systems
2. **Restart your application**:
   - Stop uvicorn (Ctrl+C in terminal)
   - Start it again: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
3. **Run indexing again**
4. **Check logs** - you should now see:
   ```
   INFO - Found X users
   INFO - Found Y attachments for user@example.com
   ```

---

## 🔍 How to Verify Permissions Are Correct

### ✅ Correct Setup:
- **User.Read.All** (Application) - ✅ Granted for [Your Organization]
- **Mail.Read** (Application) - ✅ Granted for [Your Organization]

### ❌ Common Mistakes:

1. **Wrong Permission Type:**
   - ❌ User.Read.All (Delegated) - WRONG!
   - ✅ User.Read.All (Application) - CORRECT!

2. **Not Granted:**
   - ❌ Status: "Not granted" - WRONG!
   - ✅ Status: "Granted for [Your Organization]" - CORRECT!

3. **Only One Permission:**
   - ❌ Only Mail.Read added - WRONG!
   - ✅ BOTH User.Read.All AND Mail.Read - CORRECT!

---

## 🆘 Still Getting 403 Error?

If you've added both permissions and granted admin consent, but still get 403:

1. **Double-check permission type:**
   - Must be **Application** (not Delegated)
   - Check the "Type" column in the permissions list

2. **Verify admin consent:**
   - Status must show "Granted for [Your Organization]"
   - If it shows "Not granted", click "Grant admin consent" again

3. **Wait longer:**
   - Sometimes it takes 5-10 minutes for permissions to propagate
   - Try waiting 5 minutes, then restart the app

4. **Check you're using the right app:**
   - Make sure you're adding permissions to the same app registration
   - Check the Client ID matches your `.env` file

5. **Restart application:**
   - Completely stop and restart uvicorn
   - Clear any cached tokens

---

## 📝 Quick Checklist

- [ ] Opened Azure Portal → Azure Active Directory → App registrations
- [ ] Selected the correct app registration
- [ ] Went to "API permissions"
- [ ] Added **User.Read.All** (Application permission)
- [ ] Added **Mail.Read** (Application permission)
- [ ] Clicked "Grant admin consent for [Your Organization]"
- [ ] Verified both show "Granted for [Your Organization]"
- [ ] Waited 2-3 minutes
- [ ] Restarted the application
- [ ] Ran indexing again
- [ ] Checked logs for "Found X users" (not "Found 0 users")

---

## 💡 What Should Happen After Fixing

Once permissions are correctly added and granted:

1. **Logs will show:**
   ```
   INFO - Starting email attachment indexing...
   INFO - Fetching all users for email indexing
   INFO - Found 50 users  (or whatever number of users you have)
   INFO - Fetching emails with attachments for user: user1@example.com
   INFO - Found 10 attachments for user1@example.com
   ```

2. **In the application:**
   - You'll see "Email Attachments" in the sites list
   - Files will show with source "📧 Email"
   - Email attachments will be searchable

---

If you're still having issues after following these steps, please share:
1. Screenshot of your API permissions page (showing the permissions and their status)
2. Any error messages you see

