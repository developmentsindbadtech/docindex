# Squarespace DNS Setup for docs.sindbad.tech

This guide is specifically for setting up the subdomain `docs.sindbad.tech` in Squarespace to point to Google Cloud Run.

---

## Prerequisites

- Admin access to Squarespace account
- Google Cloud Run URL (from deployment)
- CNAME target from GCP domain mapping

---

## Step-by-Step Instructions

### Step 1: Get CNAME Target from Google Cloud

Before configuring Squarespace, you need to get the CNAME target from GCP:

```bash
gcloud run domain-mappings create \
    --service sharepoint-doc-indexer \
    --domain docs.sindbad.tech \
    --region us-central1
```

**GCP will provide DNS information like:**
```
Please add the following DNS records:

Type: CNAME
Name: docs
Data: ghs.googlehosted.com
```

**Copy the "Data" value** (usually `ghs.googlehosted.com`) - this is your CNAME target.

---

### Step 2: Login to Squarespace

1. Go to https://account.squarespace.com
2. Login with admin credentials
3. Navigate to your account dashboard

---

### Step 3: Access DNS Settings for sindbad.tech

#### Option A: If sindbad.tech is a Squarespace-hosted site:

1. From your dashboard, click on **Settings**
2. Click **Domains**
3. Find **sindbad.tech** in the list
4. Click **DNS Settings** or **Advanced Settings**

#### Option B: If sindbad.tech is an externally managed domain:

1. Click on **Domains** in the main menu
2. Find **sindbad.tech**
3. Click **Manage** → **DNS Settings**

---

### Step 4: Add CNAME Record

1. In DNS Settings, look for **Custom Records** or **DNS Records**
2. Click **Add Record** or **Add New Record**
3. Select **CNAME** as the record type
4. Fill in the fields:

   **Format 1 (Most common):**
   - **Host**: `docs`
   - **Points to**: `ghs.googlehosted.com`
   - **TTL**: `3600` (or default)

   **Format 2 (If Squarespace asks for full domain):**
   - **Name**: `docs.sindbad.tech`
   - **Value**: `ghs.googlehosted.com`
   - **TTL**: `3600`

   **Format 3 (Alternative GCP target):**
   - **Host**: `docs`
   - **Points to**: `ghs.googlehosted.com.` (note the trailing dot)

5. Click **Save** or **Add Record**

---

### Step 5: Verify DNS Record Was Added

**In Squarespace:**
- You should see the new CNAME record in your DNS records list:
  ```
  Type: CNAME
  Host: docs
  Points To: ghs.googlehosted.com
  ```

**Take a screenshot** of the DNS settings for documentation.

---

### Step 6: Wait for DNS Propagation

DNS changes can take time to propagate:
- **Minimum**: 5-10 minutes
- **Typical**: 30 minutes - 2 hours  
- **Maximum**: Up to 48 hours

**Test DNS propagation:**

**Windows (PowerShell):**
```powershell
nslookup docs.sindbad.tech
```

**Mac/Linux (Terminal):**
```bash
dig docs.sindbad.tech
```

**Expected output:** You should see `ghs.googlehosted.com` in the results.

---

### Step 7: Wait for SSL Certificate (GCP Side)

After DNS propagates, Google Cloud will automatically provision an SSL certificate.

**Check certificate status:**

```bash
gcloud run domain-mappings describe \
    --domain docs.sindbad.tech \
    --region us-central1
```

Look for:
```
status:
  resourceRecords:
    - name: docs
      rrdata: ghs.googlehosted.com
      type: CNAME
  certificateStatus: READY
```

**Wait until `certificateStatus: READY`** (can take 15 minutes - 2 hours after DNS propagates).

---

### Step 8: Test Custom Domain

Once certificate is ready, test your custom domain:

```
https://docs.sindbad.tech
```

**You should see:**
- ✅ HTTPS (secure connection)
- ✅ Login page loads
- ✅ No certificate warnings

---

## Troubleshooting

### Issue: Squarespace won't let me add CNAME for subdomain

**Solution:**
- Ensure you're using the subdomain only (`docs`) not the full domain
- Try alternative formats: `docs` vs `docs.sindbad.tech`
- Check if there's an existing record for `docs` and delete it first

### Issue: DNS not propagating

**Check:**
1. Verify CNAME record exists in Squarespace
2. Wait longer (can take up to 48 hours)
3. Clear your DNS cache:
   ```powershell
   # Windows
   ipconfig /flushdns
   ```
   ```bash
   # Mac
   sudo dscacheutil -flushcache
   
   # Linux
   sudo systemd-resolve --flush-caches
   ```

### Issue: SSL certificate stuck on "Pending"

**Causes:**
- DNS not yet propagated
- CNAME record incorrect
- GCP can't verify domain ownership

**Solution:**
- Verify CNAME record is correct: `docs` → `ghs.googlehosted.com`
- Wait longer (up to 24 hours)
- Check for typos in the CNAME record

### Issue: "Too many redirects" error

**Solution:**
Update the redirect URI in Azure AD and GCP environment variables to use HTTPS:
```
https://docs.sindbad.tech/auth/callback
```

---

## Alternative: If Squarespace Doesn't Support CNAME for Subdomains

Some Squarespace plans have limitations on DNS records.

### Workaround: Use A Records

1. Get the Cloud Run IP addresses:
   ```bash
   nslookup ghs.googlehosted.com
   ```

2. Add A records in Squarespace:
   - **Host**: `docs`
   - **Value**: (IP addresses from nslookup)

**Note:** This is less ideal as Cloud Run IPs can change.

### Better Alternative: Point Domain to Cloudflare

If Squarespace has limitations:
1. Point sindbad.tech nameservers to Cloudflare
2. Manage DNS in Cloudflare (free)
3. Cloudflare has full DNS control

---

## Squarespace-Specific Notes

### If sindbad.tech is on Squarespace's Premium DNS:

- CNAME records for subdomains are supported
- Follow steps exactly as outlined above

### If sindbad.tech is on Squarespace's Basic DNS:

- May have limitations
- Consider upgrading to Premium DNS or using Cloudflare

### Squarespace Support

If you encounter issues with Squarespace:
- Contact: Squarespace Support (https://support.squarespace.com)
- Live Chat: Available 24/7
- Email: support@squarespace.com

**Ask them:** "How do I add a CNAME record for subdomain `docs` pointing to `ghs.googlehosted.com`?"

---

## DNS Record Summary

**What needs to be in Squarespace:**

```
Type: CNAME
Host/Name: docs
Points To/Value: ghs.googlehosted.com
TTL: 3600
```

**Result:**
- `docs.sindbad.tech` → `ghs.googlehosted.com` → Google Cloud Run → Your Application

---

## Verification Checklist

After DNS setup, verify:

- ✅ CNAME record exists in Squarespace DNS settings
- ✅ `nslookup docs.sindbad.tech` returns `ghs.googlehosted.com`
- ✅ GCP domain mapping status shows `READY`
- ✅ SSL certificate is provisioned
- ✅ `https://docs.sindbad.tech` loads without certificate warnings
- ✅ Login page appears
- ✅ Microsoft SSO works
- ✅ Application functions correctly

---

**Estimated Time:**
- Squarespace DNS configuration: 5 minutes
- DNS propagation: 30 minutes - 2 hours
- SSL certificate provisioning: 15 minutes - 2 hours
- **Total: 1-4 hours** (mostly waiting time)

