# 🚀 START HERE - DevOps Deployment Guide

**Application**: Sindbad.Tech SharePoint Doc Indexer  
**Deployment Target**: Google Cloud Run  
**Custom Domain**: docs.sindbad.tech (via Squarespace DNS)  
**Estimated Time**: 1-2 hours (including wait times)

---

## 📋 What You Need Before Starting

### Access & Credentials You Must Have:

1. ✅ **Google Cloud Platform Account** (with billing enabled)
2. ✅ **Squarespace Admin Access** (for DNS configuration)
3. ✅ **These Azure AD Credentials** (get from project owner):
   - Azure Tenant ID
   - Azure Client ID
   - Azure Client Secret Value

### Tools to Install:

1. ✅ **Google Cloud SDK** (gcloud CLI)
   - Download: https://cloud.google.com/sdk/docs/install
   - Install and restart terminal

2. ✅ **Git** (if not already installed)
   - To clone the repository

---

## 🎯 Deployment Steps (Follow in Order)

---

## STEP 1: Install gcloud CLI (5 minutes)

### Windows:
1. Download: https://cloud.google.com/sdk/docs/install
2. Run `GoogleCloudSDKInstaller.exe`
3. Follow the installer
4. **Restart PowerShell/Terminal**
5. Verify installation:
   ```powershell
   gcloud --version
   ```

### Mac:
```bash
brew install --cask google-cloud-sdk
gcloud --version
```

### Linux:
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud --version
```

✅ **Checkpoint**: Running `gcloud --version` should show version info.

---

## STEP 2: Login to Google Cloud (2 minutes)

```bash
# Login - this will open a browser
gcloud auth login
```

1. Browser will open
2. Select your Google account
3. Click "Allow"
4. Return to terminal

✅ **Checkpoint**: You should see "You are now logged in as [your-email]"

---

## STEP 3: Create GCP Project (3 minutes)

```bash
# Create project
gcloud projects create sindbad-sharepoint-indexer --name="Sindbad SharePoint Indexer"

# Set as active project
gcloud config set project sindbad-sharepoint-indexer

# Set default region
gcloud config set run/region us-central1

# Enable required APIs (this takes 2-3 minutes)
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

✅ **Checkpoint**: Each API should show "Operation completed successfully"

---

## STEP 4: Store Secrets Securely (5 minutes)

### A. Generate Session Secret Key

**PowerShell (Windows):**
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

**Mac/Linux:**
```bash
openssl rand -base64 32
```

**Copy the output** - this is your `SESSION_SECRET_KEY`

### B. Create Secrets (replace with actual values)

```bash
# Azure Tenant ID
echo -n "PASTE_TENANT_ID_HERE" | gcloud secrets create AZURE_TENANT_ID --data-file=-

# Azure Client ID
echo -n "PASTE_CLIENT_ID_HERE" | gcloud secrets create AZURE_CLIENT_ID --data-file=-

# Azure Client Secret
echo -n "PASTE_CLIENT_SECRET_HERE" | gcloud secrets create AZURE_CLIENT_SECRET --data-file=-

# Session Secret Key (from step 4A)
echo -n "PASTE_SESSION_SECRET_HERE" | gcloud secrets create SESSION_SECRET_KEY --data-file=-
```

**⚠️ Important**: 
- Use the actual Secret VALUE, not the Secret ID
- Don't include quotes
- No spaces before/after the value

✅ **Checkpoint**: Each command should show "Created version [1]"

### C. Grant Permissions to Secrets

```bash
# Get project number
PROJECT_NUMBER=$(gcloud projects describe sindbad-sharepoint-indexer --format="value(projectNumber)")

# Grant access
for SECRET in AZURE_TENANT_ID AZURE_CLIENT_ID AZURE_CLIENT_SECRET SESSION_SECRET_KEY; do
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
done
```

✅ **Checkpoint**: Should see "Updated IAM policy" 4 times

---

## STEP 5: Deploy Application (10 minutes)

### A. Navigate to Application Directory

```bash
# Navigate to where you cloned/have the repository
cd D:\Repository\SindbadTech\Document_Controlling
```

### B. Deploy to Cloud Run

```bash
gcloud run deploy sharepoint-doc-indexer \
    --source . \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 3600 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "HOST=0.0.0.0,PORT=8080,SSO_ALLOWED_DOMAIN=sindbad.tech" \
    --set-secrets "AZURE_TENANT_ID=AZURE_TENANT_ID:latest,AZURE_CLIENT_ID=AZURE_CLIENT_ID:latest,AZURE_CLIENT_SECRET=AZURE_CLIENT_SECRET:latest,SESSION_SECRET_KEY=SESSION_SECRET_KEY:latest"
```

**This will:**
- Build a Docker container
- Upload to Google Container Registry
- Deploy to Cloud Run

**Wait 5-10 minutes.**

When complete, you'll see:
```
Service URL: https://sharepoint-doc-indexer-XXXXX-uc.a.run.app
```

**📝 COPY THIS URL - YOU NEED IT FOR NEXT STEPS!**

✅ **Checkpoint**: You have a Cloud Run URL starting with `https://`

---

## STEP 6: Configure Azure AD Redirect URI (5 minutes)

### A. Add Cloud Run URL to Azure AD

1. Open **Azure Portal**: https://portal.azure.com
2. Go to **Azure Active Directory**
3. Click **App Registrations** (left menu)
4. Find and click: **Sindbad SharePoint Doc Indexer**
5. Click **Authentication** (left menu)
6. Scroll to **Web** → **Redirect URIs**
7. Click **+ Add URI**
8. Paste:
   ```
   https://sharepoint-doc-indexer-XXXXX-uc.a.run.app/auth/callback
   ```
   ⚠️ **Replace XXXXX with your actual Cloud Run URL**
   ⚠️ **Must end with `/auth/callback`**
9. Click **Save** (top of page)

### B. Update Environment Variable

```bash
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --update-env-vars "SSO_REDIRECT_URI=https://sharepoint-doc-indexer-XXXXX-uc.a.run.app/auth/callback"
```

⚠️ **Replace with your actual Cloud Run URL**

### C. Test the Application

1. Open your Cloud Run URL in browser
2. You should see the login page
3. Click "Sign in with Microsoft"
4. Login with a @sindbad.tech email
5. You should be redirected to the dashboard

✅ **Checkpoint**: Application loads and login works

**🎉 If login works, the application is working! Now set up custom domain...**

---

## STEP 7: Setup Custom Domain in GCP (5 minutes)

```bash
gcloud run domain-mappings create \
    --service sharepoint-doc-indexer \
    --domain docs.sindbad.tech \
    --region us-central1
```

**GCP will show:**
```
Please add the following DNS record:

Type: CNAME
Name: docs
Data: ghs.googlehosted.com
```

**📝 COPY "Data" VALUE - YOU NEED IT FOR SQUARESPACE**

Usually it's: `ghs.googlehosted.com`

✅ **Checkpoint**: Command completes without errors

---

## STEP 8: Configure DNS in Squarespace (5 minutes)

### A. Login to Squarespace

1. Go to: https://account.squarespace.com
2. Login with admin credentials

### B. Access DNS Settings

**Method 1 (Most common):**
1. From dashboard → **Settings**
2. Click **Domains**
3. Find **sindbad.tech**
4. Click **DNS Settings** or **Advanced Settings**

**Method 2:**
1. Main menu → **Domains**
2. Find **sindbad.tech**
3. Click **Manage** → **DNS Settings**

### C. Add CNAME Record

1. Look for **Custom Records** or **Add Record**
2. Click **Add Record**
3. Select **CNAME** type
4. Fill in:

   ```
   Type: CNAME
   Host: docs
   Points to: ghs.googlehosted.com
   TTL: 3600
   ```

   **⚠️ Important:**
   - Host is just `docs` (NOT `docs.sindbad.tech`)
   - Points to is `ghs.googlehosted.com` (might have trailing dot)
   - Some Squarespace versions use different field names:
     - "Host" might be "Name" or "Subdomain"
     - "Points to" might be "Value" or "Target"

5. Click **Save** or **Add**

### D. Verify Record Was Added

You should see in your DNS records list:
```
Type: CNAME
Host: docs
Target: ghs.googlehosted.com
```

**📸 Take a screenshot** for documentation

✅ **Checkpoint**: CNAME record visible in Squarespace DNS settings

---

## STEP 9: Wait for DNS Propagation (30 min - 2 hours)

### Test DNS Every 10 Minutes

**Windows:**
```powershell
nslookup docs.sindbad.tech
```

**Mac/Linux:**
```bash
dig docs.sindbad.tech
host docs.sindbad.tech
```

**What you're looking for:**
- Should return `ghs.googlehosted.com` in the result

**Online tool** (if commands don't work):
- https://dnschecker.org
- Enter: `docs.sindbad.tech`
- Type: CNAME
- Should show `ghs.googlehosted.com`

✅ **Checkpoint**: DNS resolves to `ghs.googlehosted.com`

**☕ Take a coffee break while waiting...**

---

## STEP 10: Wait for SSL Certificate (15 min - 2 hours)

After DNS propagates, check SSL certificate status:

```bash
gcloud run domain-mappings describe \
    --domain docs.sindbad.tech \
    --region us-central1
```

Look for:
```yaml
certificateStatus: READY
```

**Keep running this command every 10 minutes until status is READY.**

✅ **Checkpoint**: `certificateStatus: READY`

---

## STEP 11: Update Azure AD with Custom Domain (5 minutes)

### A. Add Custom Domain to Azure AD

1. Open **Azure Portal**: https://portal.azure.com
2. Go to **Azure Active Directory**
3. **App Registrations** → **Sindbad SharePoint Doc Indexer**
4. Click **Authentication**
5. Under **Redirect URIs**, click **+ Add URI**
6. Add:
   ```
   https://docs.sindbad.tech/auth/callback
   ```
7. Click **Save**

### B. Update Cloud Run Environment Variable

```bash
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --update-env-vars "SSO_REDIRECT_URI=https://docs.sindbad.tech/auth/callback"
```

✅ **Checkpoint**: Environment variable updated

---

## STEP 12: Final Testing (10 minutes)

### Test 1: Access Application
1. Open: https://docs.sindbad.tech
2. Should show login page
3. Should have valid SSL (🔒 padlock icon)

### Test 2: Login
1. Click "Sign in with Microsoft"
2. Login with @sindbad.tech account
3. Should redirect to dashboard

### Test 3: Basic Functionality
1. Click "Discover Sites"
2. Sites should load
3. Select a site
4. Check "Search SharePoint" and "Search Email"
5. Click "Index Selected Sites"
6. Indexing should start
7. Wait for completion
8. Files should appear in table
9. Try searching for a file
10. Click logout

✅ **Checkpoint**: All tests pass

---

## 🎉 DEPLOYMENT COMPLETE!

Your application is now live at: **https://docs.sindbad.tech**

---

## 📊 Post-Deployment Information

### Access URLs
- **Production**: https://docs.sindbad.tech
- **Cloud Run Direct**: https://sharepoint-doc-indexer-XXXXX-uc.a.run.app

### GCP Resources
- **Project**: sindbad-sharepoint-indexer
- **Service**: sharepoint-doc-indexer
- **Region**: us-central1

### View Logs
```bash
# Real-time logs
gcloud run services logs tail sharepoint-doc-indexer --region us-central1

# Recent logs
gcloud run services logs read sharepoint-doc-indexer --region us-central1 --limit 50
```

### Access GCP Console
https://console.cloud.google.com/run?project=sindbad-sharepoint-indexer

---

## 🔧 Common Issues & Solutions

### Issue: "gcloud: command not found"
**Solution**: Restart terminal after installing gcloud CLI

### Issue: "Permission denied" during deployment
**Solution**: 
```bash
gcloud auth login
gcloud auth application-default login
```

### Issue: "Billing must be enabled"
**Solution**: 
1. Go to: https://console.cloud.google.com/billing
2. Link project to billing account

### Issue: Squarespace won't let me add CNAME
**Solution**: 
- Try `docs` (just subdomain)
- Or try `docs.sindbad.tech` (full domain)
- Different Squarespace versions use different formats

### Issue: DNS not propagating
**Solution**: 
- Wait longer (can take 2-4 hours)
- Clear DNS cache: `ipconfig /flushdns` (Windows)
- Verify CNAME record in Squarespace

### Issue: SSL certificate stuck on "Pending"
**Solution**: 
- DNS must propagate first
- Wait up to 24 hours
- Verify CNAME is correct in Squarespace

### Issue: "Invalid redirect URI" when logging in
**Solution**: 
1. Verify Azure AD redirect URI matches exactly
2. Must end with `/auth/callback`
3. Check `SSO_REDIRECT_URI` environment variable in Cloud Run

---

## 📞 Support Contacts

### GCP Issues:
- GCP Support: https://cloud.google.com/support
- Documentation: https://cloud.google.com/run/docs

### Squarespace Issues:
- Support: https://support.squarespace.com
- Live Chat: Available 24/7
- Ask: "How do I add a CNAME record for subdomain 'docs' pointing to 'ghs.googlehosted.com'?"

### Azure AD Issues:
- Azure Support: https://portal.azure.com → Help + support
- Documentation: https://docs.microsoft.com/azure

### Application Issues:
- Check logs: `gcloud run services logs read sharepoint-doc-indexer`
- See: DEVOPS_DEPLOYMENT_GUIDE.md for detailed troubleshooting

---

## 🔄 Quick Reference Commands

### View Application Status
```bash
gcloud run services describe sharepoint-doc-indexer --region us-central1
```

### Update Application (after code changes)
```bash
cd /path/to/Document_Controlling
gcloud run deploy sharepoint-doc-indexer --source . --region us-central1
```

### View Logs
```bash
gcloud run services logs tail sharepoint-doc-indexer --region us-central1
```

### Update Environment Variable
```bash
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --update-env-vars "KEY=VALUE"
```

### Check Domain Mapping Status
```bash
gcloud run domain-mappings describe --domain docs.sindbad.tech --region us-central1
```

---

## ✅ Deployment Checklist

Print this and check off as you go:

- [ ] Step 1: gcloud CLI installed
- [ ] Step 2: Logged into GCP
- [ ] Step 3: Project created and APIs enabled
- [ ] Step 4: All secrets created and permissions granted
- [ ] Step 5: Application deployed to Cloud Run
- [ ] Step 6: Azure AD redirect URI added for Cloud Run URL
- [ ] Step 7: Domain mapping created in GCP
- [ ] Step 8: CNAME record added in Squarespace
- [ ] Step 9: DNS propagated (verified with nslookup)
- [ ] Step 10: SSL certificate ready
- [ ] Step 11: Azure AD redirect URI added for custom domain
- [ ] Step 12: All tests passed

**Deployment Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Completed

**Deployed by**: _________________ **Date**: _________

---

## 📄 Additional Documentation

If you need more details, see:
- `DEVOPS_DEPLOYMENT_GUIDE.md` - Comprehensive technical guide
- `SQUARESPACE_DNS_SETUP.md` - Detailed DNS instructions
- `DEPLOYMENT_CHECKLIST.md` - Detailed checklist with testing

---

**Questions?** Check the troubleshooting section above or detailed guides.

**Ready?** Start with Step 1! 🚀

