# Deployment Checklist - DevOps

Use this checklist to ensure all deployment steps are completed correctly.

---

## Pre-Deployment Checklist

### Azure AD Setup
- [ ] Azure AD App Registration created
- [ ] Client ID obtained
- [ ] Client Secret created and securely stored
- [ ] Tenant ID obtained
- [ ] API Permissions granted:
  - [ ] `Sites.Read.All` (Application) - Admin consent granted
  - [ ] `User.Read.All` (Application) - Admin consent granted
  - [ ] `Mail.Read` (Application) - Admin consent granted
  - [ ] `User.Read` (Delegated)
  - [ ] `email` (Delegated)

### Google Cloud Setup
- [ ] GCP account created
- [ ] Billing enabled
- [ ] gcloud CLI installed
- [ ] Project created: `sindbad-sharepoint-indexer`
- [ ] Required APIs enabled:
  - [ ] Cloud Run API
  - [ ] Cloud Build API
  - [ ] Secret Manager API
  - [ ] Container Registry API

---

## Deployment Steps

### Phase 1: GCP Secret Manager (10 min)
- [ ] Created `AZURE_TENANT_ID` secret
- [ ] Created `AZURE_CLIENT_ID` secret
- [ ] Created `AZURE_CLIENT_SECRET` secret
- [ ] Created `SESSION_SECRET_KEY` secret (randomly generated)
- [ ] Granted Cloud Run service account access to all secrets
- [ ] Verified secrets are accessible

### Phase 2: Deploy to Cloud Run (10 min)
- [ ] Navigated to project directory
- [ ] Ran deployment command
- [ ] Deployment completed successfully
- [ ] Copied Cloud Run URL: `https://sharepoint-doc-indexer-XXXXX-uc.a.run.app`
- [ ] Tested Cloud Run URL (should show error about redirect URI - this is expected)

### Phase 3: Azure AD Redirect URI - Temporary (5 min)
- [ ] Opened Azure Portal
- [ ] Added Cloud Run URL to redirect URIs: `https://sharepoint-doc-indexer-XXXXX-uc.a.run.app/auth/callback`
- [ ] Saved changes
- [ ] Updated `SSO_REDIRECT_URI` environment variable in Cloud Run
- [ ] Tested login works with Cloud Run URL

### Phase 4: Squarespace DNS Setup (5 min + wait time)
- [ ] Created domain mapping in GCP for `docs.sindbad.tech`
- [ ] Noted the CNAME target (usually `ghs.googlehosted.com`)
- [ ] Logged into Squarespace
- [ ] Accessed DNS settings for sindbad.tech
- [ ] Added CNAME record:
  - Host: `docs`
  - Points to: `ghs.googlehosted.com`
- [ ] Saved DNS record
- [ ] Took screenshot of DNS settings
- [ ] Waited for DNS propagation (verify with `nslookup docs.sindbad.tech`)
- [ ] Verified DNS points to `ghs.googlehosted.com`

### Phase 5: SSL Certificate (15 min - 2 hours wait)
- [ ] Checked domain mapping status in GCP
- [ ] Waited for `certificateStatus: READY`
- [ ] Verified `https://docs.sindbad.tech` loads with valid SSL

### Phase 6: Azure AD Redirect URI - Final (5 min)
- [ ] Added custom domain to Azure AD redirect URIs: `https://docs.sindbad.tech/auth/callback`
- [ ] Updated `SSO_REDIRECT_URI` environment variable in Cloud Run to custom domain
- [ ] Tested login with custom domain

### Phase 7: Final Testing (10 min)
- [ ] Opened `https://docs.sindbad.tech`
- [ ] Clicked "Sign in with Microsoft"
- [ ] Logged in with @sindbad.tech account
- [ ] Redirected successfully to application
- [ ] Clicked "Discover Sites"
- [ ] Sites loaded successfully
- [ ] Selected a site with both options (SharePoint + Email)
- [ ] Clicked "Index Selected Sites"
- [ ] Indexing started successfully
- [ ] Indexing completed successfully
- [ ] Files displayed in table
- [ ] Search functionality works
- [ ] Logout works

---

## Post-Deployment Verification

### Functionality Tests
- [ ] Login/Logout works
- [ ] Site discovery works
- [ ] SharePoint indexing works
- [ ] Email indexing works
- [ ] Search works (including Arabic characters)
- [ ] File links open correctly
- [ ] Progress bar animates correctly
- [ ] "Stop & Reset All" works
- [ ] Incremental updates work

### Performance Tests
- [ ] Application loads within 3 seconds
- [ ] Indexing completes without timeouts
- [ ] Search returns results quickly
- [ ] No memory issues during indexing

### Security Tests
- [ ] Only @sindbad.tech users can login
- [ ] Other domain users are rejected
- [ ] Logout clears session
- [ ] HTTPS is enforced
- [ ] No secrets visible in logs
- [ ] No secrets in client-side code

---

## Documentation to Provide

After successful deployment, provide:

1. **Access URLs**
   - Production: https://docs.sindbad.tech
   - Cloud Run: https://sharepoint-doc-indexer-XXXXX-uc.a.run.app

2. **GCP Information**
   - Project ID: `sindbad-sharepoint-indexer`
   - Region: `us-central1`
   - Service Name: `sharepoint-doc-indexer`

3. **Monitoring Links**
   - GCP Console: https://console.cloud.google.com/run?project=sindbad-sharepoint-indexer
   - Logs: Instructions in DEVOPS_DEPLOYMENT_GUIDE.md

4. **Screenshots**
   - Squarespace DNS settings
   - GCP domain mapping status
   - Azure AD redirect URIs
   - Working application

5. **Credentials Location**
   - All secrets stored in GCP Secret Manager
   - No credentials in code or config files

---

## Sign-Off

**Deployment completed by:** _________________

**Date:** _________________

**Tested by:** _________________

**Approved by:** _________________

---

## Maintenance Schedule

### Regular Tasks
- **Weekly**: Check application logs for errors
- **Monthly**: Review and rotate secrets (if needed)
- **Quarterly**: Update dependencies and redeploy

### Monitoring
- Set up GCP monitoring alerts (optional)
- Monitor costs in GCP Billing

---

**Deployment Status:** ⬜ Not Started | ⬜ In Progress | ⬜ Completed | ⬜ Issues

**Notes:**
_________________________________________
_________________________________________
_________________________________________

