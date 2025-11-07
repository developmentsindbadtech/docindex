# DevOps Deployment Guide - Sindbad.Tech SharePoint Doc Indexer

This guide provides complete step-by-step instructions for deploying the SharePoint Doc Indexer application to Google Cloud Run with a custom subdomain (docs.sindbad.tech) managed through Squarespace.

---

## Overview

- **Application**: Sindbad.Tech SharePoint Doc Indexer (Python FastAPI)
- **Hosting**: Google Cloud Platform - Cloud Run
- **Domain**: docs.sindbad.tech (managed via Squarespace)
- **Authentication**: Microsoft Azure AD (SSO)

---

## Part 1: Google Cloud Platform Setup

### Prerequisites
- GCP account with billing enabled
- gcloud CLI installed
- Access to the application repository

### Step 1.1: Install Google Cloud SDK (if not installed)

**Windows:**
1. Download installer: https://cloud.google.com/sdk/docs/install
2. Run the installer
3. Restart terminal/PowerShell

**Mac:**
```bash
brew install --cask google-cloud-sdk
```

**Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### Step 1.2: Initialize gcloud CLI

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create sindbad-sharepoint-indexer --name="Sindbad SharePoint Indexer"

# Set the project as active
gcloud config set project sindbad-sharepoint-indexer

# Set default region
gcloud config set run/region us-central1

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable containerregistry.gcr.io
```

**Expected Output:** "Operation completed successfully" for each API enablement.

### Step 1.3: Get Your Project Number (needed for secrets)

```bash
gcloud projects describe sindbad-sharepoint-indexer --format="value(projectNumber)"
```

**Copy this number** - you'll need it for the next step.

### Step 1.4: Create Secrets in Secret Manager

Replace `YOUR_PROJECT_NUMBER` with the number from Step 1.3:

```bash
# Create secret for Azure Tenant ID
echo -n "YOUR_AZURE_TENANT_ID" | gcloud secrets create AZURE_TENANT_ID --data-file=-

# Create secret for Azure Client ID
echo -n "YOUR_AZURE_CLIENT_ID" | gcloud secrets create AZURE_CLIENT_ID --data-file=-

# Create secret for Azure Client Secret
echo -n "YOUR_AZURE_CLIENT_SECRET" | gcloud secrets create AZURE_CLIENT_SECRET --data-file=-

# Create secret for Session Secret Key (generate a random 32-character string)
echo -n "GENERATE_RANDOM_32_CHAR_STRING" | gcloud secrets create SESSION_SECRET_KEY --data-file=-
```

**To generate a random session key:**

**PowerShell (Windows):**
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

**Linux/Mac:**
```bash
openssl rand -base64 32
```

### Step 1.5: Grant Cloud Run Access to Secrets

```bash
# Get your project number first
PROJECT_NUMBER=$(gcloud projects describe sindbad-sharepoint-indexer --format="value(projectNumber)")

# Grant access to all secrets
for SECRET in AZURE_TENANT_ID AZURE_CLIENT_ID AZURE_CLIENT_SECRET SESSION_SECRET_KEY; do
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
done
```

**Expected Output:** "Updated IAM policy" for each secret.

### Step 1.6: Deploy Application to Cloud Run

Navigate to the application directory:

```bash
cd /path/to/Document_Controlling
```

Deploy the application:

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

**This will take 5-10 minutes.**

When complete, you'll see:
```
Service URL: https://sharepoint-doc-indexer-XXXXX-uc.a.run.app
```

**Copy this URL** - you'll need it for the next steps.

### Step 1.7: Test the Deployment

Open the Cloud Run URL in your browser:
```
https://sharepoint-doc-indexer-XXXXX-uc.a.run.app
```

You should see an error about Azure AD redirect URI (this is expected - we'll fix it next).

---

## Part 2: Azure AD Configuration

### Step 2.1: Add Cloud Run URL to Azure AD Redirect URIs

1. Go to **Azure Portal** (https://portal.azure.com)
2. Navigate to **Azure Active Directory**
3. Click **App Registrations**
4. Find and select: **Sindbad SharePoint Doc Indexer**
5. Click **Authentication** (left menu)
6. Under **Platform configurations** → **Web** → **Redirect URIs**
7. Click **Add URI**
8. Add:
   ```
   https://sharepoint-doc-indexer-XXXXX-uc.a.run.app/auth/callback
   ```
   (Replace with your actual Cloud Run URL)
9. Click **Save**

### Step 2.2: Update SSO_REDIRECT_URI Environment Variable

```bash
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --update-env-vars "SSO_REDIRECT_URI=https://sharepoint-doc-indexer-XXXXX-uc.a.run.app/auth/callback"
```

(Replace with your actual Cloud Run URL)

### Step 2.3: Test Authentication

1. Open your Cloud Run URL
2. Click "Sign in with Microsoft"
3. Sign in with a @sindbad.tech account
4. You should be redirected back to the application

**If authentication works, proceed to custom domain setup.**

---

## Part 3: Squarespace DNS Configuration

### Step 3.1: Get Cloud Run Domain Mapping Information

Run this command to create the domain mapping:

```bash
gcloud run domain-mappings create \
    --service sharepoint-doc-indexer \
    --domain docs.sindbad.tech \
    --region us-central1
```

**GCP will provide DNS records** that look like:

```
Type: CNAME
Name: docs
Value: ghs.googlehosted.com
```

**Copy these DNS records** - you'll need them for Squarespace.

### Step 3.2: Add DNS Records in Squarespace

**Instructions for DevOps:**

1. **Login to Squarespace**
   - Go to https://account.squarespace.com
   - Login with admin credentials

2. **Navigate to DNS Settings**
   - Click on the **sindbad.tech** domain
   - Go to **DNS Settings** or **Advanced DNS**

3. **Add CNAME Record**
   - Click **Add Record**
   - Select **CNAME Record**
   - Fill in:
     - **Host**: `docs`
     - **Points to**: `ghs.googlehosted.com` (or the value provided by GCP)
     - **TTL**: 3600 (1 hour)
   - Click **Save**

4. **Alternative: If Squarespace requires full domain**
   - **Host/Name**: `docs.sindbad.tech`
   - **Points to**: `ghs.googlehosted.com`

**Screenshot:** Take a screenshot of the DNS settings after saving.

### Step 3.3: Verify DNS Records

Wait 5-10 minutes, then verify DNS propagation:

**Windows (PowerShell):**
```powershell
nslookup docs.sindbad.tech
```

**Linux/Mac:**
```bash
dig docs.sindbad.tech
host docs.sindbad.tech
```

**Expected Output:** You should see `ghs.googlehosted.com` in the result.

### Step 3.4: Wait for SSL Certificate

After DNS is configured, GCP automatically provisions an SSL certificate for your custom domain.

**Check certificate status:**
```bash
gcloud run domain-mappings describe \
    --domain docs.sindbad.tech \
    --region us-central1
```

**This can take up to 24 hours** (usually 15-30 minutes).

Status will change from `CertificatePending` to `CertificateReady`.

### Step 3.5: Test Custom Domain

Once the certificate is ready, test the custom domain:

```
https://docs.sindbad.tech
```

You should see the login page.

---

## Part 4: Final Azure AD Configuration

### Step 4.1: Add Custom Domain to Azure AD Redirect URIs

1. Go to **Azure Portal** (https://portal.azure.com)
2. Navigate to **Azure Active Directory**
3. Click **App Registrations**
4. Find and select: **Sindbad SharePoint Doc Indexer**
5. Click **Authentication**
6. Under **Redirect URIs**, click **Add URI**
7. Add:
   ```
   https://docs.sindbad.tech/auth/callback
   ```
8. Click **Save**

### Step 4.2: Update Cloud Run Environment Variable

```bash
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --update-env-vars "SSO_REDIRECT_URI=https://docs.sindbad.tech/auth/callback"
```

### Step 4.3: Final Test

1. Open: https://docs.sindbad.tech
2. Click "Sign in with Microsoft"
3. Login with @sindbad.tech account
4. You should be redirected to the application dashboard
5. Click "Discover Sites"
6. Select sites and options
7. Click "Index Selected Sites"
8. Verify indexing works

**If everything works, deployment is complete! ✅**

---

## Part 5: Monitoring & Maintenance

### View Live Logs

```bash
# Real-time logs
gcloud run services logs tail sharepoint-doc-indexer --region us-central1

# Recent logs (last 50 lines)
gcloud run services logs read sharepoint-doc-indexer --region us-central1 --limit 50
```

### Check Application Status

```bash
gcloud run services describe sharepoint-doc-indexer --region us-central1
```

### Update Application (After Code Changes)

```bash
# Redeploy from source
gcloud run deploy sharepoint-doc-indexer \
    --source . \
    --region us-central1
```

### Scale Resources (if needed)

```bash
# Increase memory/CPU
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --memory 2Gi \
    --cpu 2

# Adjust instance limits
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --min-instances 0 \
    --max-instances 20
```

### Update Environment Variables

```bash
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --update-env-vars "KEY=VALUE"
```

### Update Secrets

```bash
# Update a secret value
echo -n "NEW_VALUE" | gcloud secrets versions add AZURE_CLIENT_SECRET --data-file=-

# Cloud Run will automatically use the latest version
```

---

## Part 6: Troubleshooting

### Issue: Application won't start

**Check logs:**
```bash
gcloud run services logs read sharepoint-doc-indexer --region us-central1 --limit 100
```

**Common causes:**
- Missing environment variables
- Invalid Azure credentials
- Secrets not accessible

### Issue: Authentication fails

**Check:**
1. Azure AD redirect URI matches exactly: `https://docs.sindbad.tech/auth/callback`
2. SSO_REDIRECT_URI environment variable is set correctly
3. Azure AD permissions are granted (User.Read, Mail.Read, Sites.Read.All)

### Issue: Custom domain not working

**Check DNS:**
```bash
nslookup docs.sindbad.tech
```

**Verify domain mapping:**
```bash
gcloud run domain-mappings describe --domain docs.sindbad.tech --region us-central1
```

**Wait for SSL certificate** - can take up to 24 hours.

### Issue: Indexing fails

**Check Azure AD permissions in Azure Portal:**
1. Go to App Registrations
2. Select your app
3. Click **API permissions**
4. Verify these permissions are granted and have admin consent:
   - `Sites.Read.All` (Application)
   - `User.Read.All` (Application)
   - `Mail.Read` (Application)
   - `User.Read` (Delegated)

---

## Part 7: Cost Estimates

### Google Cloud Run
- **Free Tier**: 2 million requests/month
- **Estimated Cost**: $5-15/month for typical usage
- **Billing**: Pay per use (only when running)

### Squarespace Domain
- Already included in Squarespace subscription
- No additional cost for DNS management

---

## Part 8: Security Checklist

Before going live, verify:

- ✅ All secrets stored in GCP Secret Manager (not in code)
- ✅ Session secret key is strong and random
- ✅ Azure client secret is secure
- ✅ SSL certificate is active (https://)
- ✅ Only @sindbad.tech emails can access
- ✅ Azure AD permissions are correctly set
- ✅ Application logs don't expose sensitive data

---

## Part 9: Rollback Procedure (If Needed)

### Rollback to Previous Version

```bash
# List revisions
gcloud run revisions list --service sharepoint-doc-indexer --region us-central1

# Rollback to specific revision
gcloud run services update-traffic sharepoint-doc-indexer \
    --region us-central1 \
    --to-revisions REVISION_NAME=100
```

### Emergency: Take Service Offline

```bash
# Scale to zero instances
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --max-instances 0
```

### Restore Service

```bash
# Restore normal scaling
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --max-instances 10
```

---

## Summary of URLs and Credentials

**After deployment, document these:**

| Item | Value |
|------|-------|
| Cloud Run URL | https://sharepoint-doc-indexer-XXXXX-uc.a.run.app |
| Custom Domain | https://docs.sindbad.tech |
| GCP Project ID | sindbad-sharepoint-indexer |
| GCP Region | us-central1 |
| Azure Tenant ID | (in Secret Manager) |
| Azure Client ID | (in Secret Manager) |
| Azure Redirect URI | https://docs.sindbad.tech/auth/callback |

**Keep this information secure and share only with authorized personnel.**

---

## Contact for Issues

- **GCP Issues**: Check GCP Console → Cloud Run → Logs
- **DNS Issues**: Verify Squarespace DNS settings
- **Azure AD Issues**: Check Azure Portal → App Registrations
- **Application Issues**: Check application logs in GCP

---

**Deployment should take 30-60 minutes total** (including DNS propagation wait time).

