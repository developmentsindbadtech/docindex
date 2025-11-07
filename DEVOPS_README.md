# 📦 For DevOps Team

## Quick Start

**👉 START HERE**: Read `START_HERE_DEVOPS.md` first

This is a Python FastAPI web application that needs to be deployed to **Google Cloud Run** with a custom domain.

---

## What's Included in This Repository

### Application Code
- `app/` - Python FastAPI application
- `static/` - Frontend (HTML, CSS, JavaScript)
- `requirements.txt` - Python dependencies

### Deployment Files
- `Dockerfile` - Container configuration
- `.dockerignore` - Files to exclude from Docker build
- `cloudbuild.yaml` - Automated build configuration
- `.gcloudignore` - Files to exclude from gcloud deployments

### Documentation for Deployment
1. **START_HERE_DEVOPS.md** ⭐ - **READ THIS FIRST**
2. **DEVOPS_DEPLOYMENT_GUIDE.md** - Comprehensive technical guide
3. **SQUARESPACE_DNS_SETUP.md** - DNS configuration steps
4. **DEPLOYMENT_CHECKLIST.md** - Checklist format

### Other Documentation
- `README.md` - General application overview
- `SETUP_EMAIL_PERMISSIONS.md` - Azure AD email permissions
- `SETUP_SSO.md` - Azure AD SSO setup
- Various other setup guides

---

## Required Access

Before starting, ensure you have:

1. ✅ **Google Cloud Platform account** (with billing)
2. ✅ **Squarespace admin access** (DNS configuration)
3. ✅ **Azure AD credentials** (from project owner):
   - Azure Tenant ID
   - Azure Client ID
   - Azure Client Secret

---

## Deployment Overview

```
1. Install gcloud CLI (5 min)
2. Login to GCP (2 min)
3. Create GCP project (3 min)
4. Store secrets (5 min)
5. Deploy to Cloud Run (10 min)
6. Configure Azure AD (5 min)
7. Setup GCP domain mapping (5 min)
8. Configure Squarespace DNS (5 min)
9. Wait for DNS propagation (30 min - 2 hours)
10. Wait for SSL certificate (15 min - 2 hours)
11. Update Azure AD with custom domain (5 min)
12. Test (10 min)

Total Active Time: ~1 hour
Total Wait Time: 1-4 hours
```

---

## Deployment Command (Quick Copy)

After setting up secrets, this is the main deployment command:

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

---

## DNS Record for Squarespace

Add this CNAME record in Squarespace DNS:

```
Type: CNAME
Host: docs
Points to: ghs.googlehosted.com
TTL: 3600
```

---

## Expected Result

After successful deployment:
- ✅ Application accessible at: https://docs.sindbad.tech
- ✅ Valid SSL certificate (HTTPS)
- ✅ Login with Microsoft SSO works
- ✅ Only @sindbad.tech users can access
- ✅ SharePoint indexing works
- ✅ Email attachment indexing works
- ✅ Search functionality works

---

## Technology Stack

- **Backend**: Python 3.11 + FastAPI
- **Frontend**: HTML5 + JavaScript (Vanilla)
- **Authentication**: Microsoft Azure AD (OAuth 2.0 / OpenID Connect)
- **APIs**: Microsoft Graph API (SharePoint, Mail)
- **Hosting**: Google Cloud Run (serverless containers)
- **DNS**: Squarespace
- **SSL**: Google-managed certificates

---

## Architecture

```
User Browser
    ↓ (HTTPS)
docs.sindbad.tech (Squarespace DNS)
    ↓ (CNAME)
ghs.googlehosted.com (Google Cloud)
    ↓
Cloud Run Service (this application)
    ↓
Microsoft Graph API (SharePoint + Email data)
```

---

## Cost Estimate

### Google Cloud Run
- **Free tier**: 2 million requests/month
- **Estimated**: $5-15/month for typical usage
- **Billing**: Pay only when requests are being processed

### Squarespace
- No additional cost (DNS included in subscription)

### Microsoft 365
- Already included in existing subscription

**Total Additional Cost: ~$5-15/month**

---

## Security Features

- ✅ Microsoft SSO (Azure AD)
- ✅ Domain restriction (@sindbad.tech only)
- ✅ Secrets stored in GCP Secret Manager
- ✅ HTTPS enforced
- ✅ Session-based authentication
- ✅ No database (data in memory only)
- ✅ Runs as non-root user

---

## Maintenance

### Regular Updates
```bash
# Pull latest code
git pull

# Redeploy
gcloud run deploy sharepoint-doc-indexer --source . --region us-central1
```

### View Application Logs
```bash
gcloud run services logs read sharepoint-doc-indexer --region us-central1
```

### Monitor Costs
https://console.cloud.google.com/billing

---

## Support

### First, Check:
1. Application logs in GCP
2. Azure AD permissions in Azure Portal
3. Environment variables in Cloud Run
4. DNS settings in Squarespace

### Then:
- See detailed troubleshooting in `START_HERE_DEVOPS.md`
- Contact project owner
- Check GCP/Azure documentation

---

## Files DevOps Needs

**Minimum files needed:**
1. `START_HERE_DEVOPS.md` ⭐⭐⭐
2. This entire repository

**Optional (for reference):**
- `DEVOPS_DEPLOYMENT_GUIDE.md`
- `SQUARESPACE_DNS_SETUP.md`

---

**👉 Next Step**: Open `START_HERE_DEVOPS.md` and follow the steps!

