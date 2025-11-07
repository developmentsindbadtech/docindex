# Setting Up Microsoft SSO Authentication

This guide will help you configure Microsoft Single Sign-On (SSO) to restrict access to Sindbad employees only.

## Prerequisites

- Azure AD administrator access
- Your existing Azure AD App Registration (the same one used for SharePoint access)

## Step 1: Update Azure AD App Registration

### 1.1 Add Redirect URI

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Select your existing app registration (the one you created for SharePoint)
4. Go to **"Authentication"** in the left menu
5. Under **"Platform configurations"**, click **"Add a platform"**
6. Select **"Web"**
7. Add your redirect URI:
   - **For local development**: `http://localhost:8000/auth/callback`
   - **For production**: `https://docs.sindbad.tech/auth/callback`
8. Click **"Configure"**

### 1.2 Add Delegated Permissions

1. Go to **"API permissions"** in the left menu
2. Click **"Add a permission"**
3. Select **"Microsoft Graph"**
4. Choose **"Delegated permissions"** (not Application permissions)
5. Add these permissions:
   - `User.Read` - Sign in and read user profile
   - `openid` - Sign users in
   - `profile` - View users' basic profile
   - `email` - View users' email address
6. Click **"Add permissions"**
7. **Grant admin consent** for your organization

### 1.3 Configure Token Settings (Optional but Recommended)

1. Go to **"Token configuration"**
2. Click **"Add optional claim"**
3. Select **"ID"** token type
4. Check **"email"** and **"upn"** (User Principal Name)
5. Click **"Add"**

## Step 2: Update Environment Variables

Add these new variables to your `.env` file:

```env
# Existing Azure AD credentials (keep these)
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here

# SSO Settings
SSO_REDIRECT_URI=http://localhost:8000/auth/callback
# For production, use: https://docs.sindbad.tech/auth/callback
SSO_ALLOWED_DOMAIN=sindbad.tech
SESSION_SECRET_KEY=change-this-to-a-random-secret-key-in-production
```

### Important: Session Secret Key

**Generate a secure random key for production:**

```powershell
# In PowerShell, generate a random secret key:
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
```

Or use an online generator. The key should be:
- At least 32 characters long
- Random and unpredictable
- Different for each environment (dev, staging, production)

## Step 3: Install New Dependencies

```powershell
pip install itsdangerous>=2.1.2 python-multipart>=0.0.6
```

Or reinstall all dependencies:

```powershell
pip install -r requirements.txt
```

## Step 4: Test the Authentication

1. Start your application:
   ```powershell
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Open your browser and go to: `http://localhost:8000`

3. You should be redirected to the login page

4. Click **"Sign in with Microsoft"**

5. Sign in with a @sindbad.tech email address

6. You should be redirected back to the application

## How It Works

1. **User visits the app** → Redirected to login if not authenticated
2. **User clicks "Sign in with Microsoft"** → Redirected to Microsoft login
3. **User signs in** → Microsoft redirects back with authorization code
4. **App exchanges code for token** → Gets user information
5. **Domain validation** → Checks if email is @sindbad.tech
6. **Session created** → User is authenticated and can access the app
7. **All API routes protected** → Require authentication

## Security Features

- ✅ **Domain restriction**: Only @sindbad.tech emails allowed
- ✅ **CSRF protection**: State parameter prevents cross-site attacks
- ✅ **Session management**: Secure session cookies
- ✅ **Automatic logout**: Sessions expire after 24 hours
- ✅ **Protected routes**: All API endpoints require authentication

## Troubleshooting

### "Access denied - domain not allowed"
- Check that your email ends with `@sindbad.tech`
- Verify `SSO_ALLOWED_DOMAIN` in `.env` is set to `sindbad.tech`

### "Redirect URI mismatch"
- Ensure the redirect URI in Azure Portal matches exactly:
  - Local: `http://localhost:8000/auth/callback`
  - Production: `https://your-subdomain.sindbad.tech/auth/callback`
- Check `SSO_REDIRECT_URI` in `.env` matches

### "Authentication failed"
- Verify all API permissions are granted and admin consent is given
- Check that delegated permissions (not application permissions) are added
- Ensure `User.Read` permission is granted

### Session not persisting
- Check `SESSION_SECRET_KEY` is set in `.env`
- Ensure cookies are enabled in your browser
- For production, ensure HTTPS is used (required for secure cookies)

## Production Deployment

When deploying to your subdomain:

1. **Update redirect URI in Azure Portal**:
   - Add: `https://docs.sindbad.tech/auth/callback`

2. **Update `.env` file**:
   ```env
   SSO_REDIRECT_URI=https://docs.sindbad.tech/auth/callback
   SESSION_SECRET_KEY=your-production-secret-key-here
   ```

3. **Ensure HTTPS is enabled** (required for secure sessions)

4. **Update CORS settings** in `app/main.py` if needed:
   ```python
   allow_origins=["https://docs.sindbad.tech"]
   ```

## Notes

- The same Azure AD App Registration is used for both:
  - **Application permissions** (for SharePoint access - existing)
  - **Delegated permissions** (for user SSO - new)
- Users must have a valid @sindbad.tech Microsoft account
- Sessions last 24 hours, then users need to sign in again

