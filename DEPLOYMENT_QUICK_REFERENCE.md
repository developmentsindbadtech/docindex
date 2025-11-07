# 📄 One-Page Deployment Quick Reference

**Print this page and follow step-by-step**

---

## Prerequisites Needed:
- [ ] Google Cloud account (billing enabled)
- [ ] Squarespace admin login
- [ ] Azure Tenant ID: `___________________________`
- [ ] Azure Client ID: `___________________________`
- [ ] Azure Client Secret: `___________________________`

---

## Commands to Run (Copy & Execute in Order)

### 1. Install & Login (5 min)
```bash
# Install gcloud from: https://cloud.google.com/sdk/docs/install
# Then restart terminal and run:
gcloud auth login
```

### 2. Create Project (3 min)
```bash
gcloud projects create sindbad-sharepoint-indexer
gcloud config set project sindbad-sharepoint-indexer
gcloud config set run/region us-central1
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

### 3. Create Secrets (5 min)
```bash
# Generate session key first (PowerShell):
# -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})

echo -n "TENANT_ID" | gcloud secrets create AZURE_TENANT_ID --data-file=-
echo -n "CLIENT_ID" | gcloud secrets create AZURE_CLIENT_ID --data-file=-
echo -n "CLIENT_SECRET" | gcloud secrets create AZURE_CLIENT_SECRET --data-file=-
echo -n "SESSION_KEY" | gcloud secrets create SESSION_SECRET_KEY --data-file=-

PROJECT_NUMBER=$(gcloud projects describe sindbad-sharepoint-indexer --format="value(projectNumber)")
for SECRET in AZURE_TENANT_ID AZURE_CLIENT_ID AZURE_CLIENT_SECRET SESSION_SECRET_KEY; do
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
done
```

### 4. Deploy (10 min)
```bash
cd D:\Repository\SindbadTech\Document_Controlling

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

**Copy Cloud Run URL**: `https://sharepoint-doc-indexer-XXXXX-uc.a.run.app`

### 5. Azure AD - Add Cloud Run URL (5 min)
1. Azure Portal → Azure AD → App Registrations
2. Select app → Authentication → Add URI:
   `https://YOUR_CLOUD_RUN_URL/auth/callback`
3. Save

```bash
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --update-env-vars "SSO_REDIRECT_URI=https://YOUR_CLOUD_RUN_URL/auth/callback"
```

**Test**: Open Cloud Run URL, login should work

### 6. Setup Custom Domain (5 min)
```bash
gcloud run domain-mappings create \
    --service sharepoint-doc-indexer \
    --domain docs.sindbad.tech \
    --region us-central1
```

**Note the CNAME target**: Usually `ghs.googlehosted.com`

### 7. Squarespace DNS (5 min)
1. Login: https://account.squarespace.com
2. Go to: sindbad.tech → DNS Settings
3. Add CNAME Record:
   - **Host**: `docs`
   - **Points to**: `ghs.googlehosted.com`
   - **TTL**: `3600`
4. Save

### 8. Wait for DNS (30 min - 2 hours)
```bash
# Test every 10 minutes
nslookup docs.sindbad.tech
# Should return: ghs.googlehosted.com
```

### 9. Wait for SSL (15 min - 2 hours)
```bash
# Check status every 10 minutes
gcloud run domain-mappings describe --domain docs.sindbad.tech --region us-central1
# Wait for: certificateStatus: READY
```

### 10. Azure AD - Add Custom Domain (5 min)
1. Azure Portal → App Registrations → Authentication
2. Add URI: `https://docs.sindbad.tech/auth/callback`
3. Save

```bash
gcloud run services update sharepoint-doc-indexer \
    --region us-central1 \
    --update-env-vars "SSO_REDIRECT_URI=https://docs.sindbad.tech/auth/callback"
```

### 11. Test (5 min)
- Open: https://docs.sindbad.tech
- Login with @sindbad.tech account
- Test indexing

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| gcloud not found | Restart terminal after installing |
| DNS not working | Wait longer, verify CNAME in Squarespace |
| SSL pending | Wait up to 24 hours after DNS propagates |
| Login fails | Check Azure redirect URI matches exactly |

---

## View Logs
```bash
gcloud run services logs tail sharepoint-doc-indexer --region us-central1
```

---

## Update Application
```bash
cd /path/to/repo
gcloud run deploy sharepoint-doc-indexer --source . --region us-central1
```

---

**Total Time: 1-4 hours (mostly waiting for DNS/SSL)**

**Questions?** See `START_HERE_DEVOPS.md` for detailed instructions.

