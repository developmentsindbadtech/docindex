# Create a New Client Secret (Step-by-Step)

## Why You Need a New Secret

Azure only shows the secret value **once** when you create it. After that, it's hidden for security. Since you can't see the full value anymore, you need to create a new one.

## Step-by-Step Instructions

### Step 1: Go to Azure Portal

1. Open [Azure Portal](https://portal.azure.com)
2. Sign in with your admin account
3. In the search bar at the top, type: **"App registrations"**
4. Click on **"App registrations"** from the results

### Step 2: Find Your App

1. Look for your app (the one you created earlier)
2. You can search by name or by the Client ID: `467e4e93-dfe0-48d7-9a5d-697aeeb5b7b0`
3. Click on the app name to open it

### Step 3: Go to Certificates & Secrets

1. In the left menu, under **"Manage"**, click **"Certificates & secrets"**
2. You'll see a page with two tabs: **"Certificates"** and **"Client secrets"**
3. Make sure you're on the **"Client secrets"** tab

### Step 4: Create New Secret

1. Click the **"+ New client secret"** button (usually at the top)
2. A dialog box will appear with:
   - **Description**: Type something like `SharePoint Indexer Secret v2` or `SharePoint Indexer - New`
   - **Expires**: Choose **24 months** (or your preferred duration)
3. Click **"Add"**

### Step 5: Copy the Value IMMEDIATELY

**THIS IS CRITICAL - DO THIS RIGHT AWAY:**

1. As soon as you click "Add", a new row will appear in the table
2. In the **"Value"** column, you'll see the full secret value
3. It will look something like: `Z5l~abc123~XYZ789~SecretValue~Here`
4. **Click on the value** or use the copy icon next to it
5. **Copy it immediately** - you have about 30 seconds before it gets hidden!

**The value will look like this:**
```
Z5l~abc123~XYZ789~SecretValue~Here
```

### Step 6: Update Your .env File

1. Open your `.env` file:
   ```powershell
   notepad .env
   ```

2. Find this line:
   ```
   AZURE_CLIENT_SECRET=Z5l******************
   ```

3. Replace it with the NEW secret value you just copied:
   ```
   AZURE_CLIENT_SECRET=Z5l~abc123~XYZ789~SecretValue~Here
   ```
   (Use the actual value you copied, not this example)

4. **Important**:
   - Don't include quotes
   - Don't include spaces
   - Copy the ENTIRE value (it's usually quite long)
   - Make sure there are no extra characters

5. Save the file (Ctrl+S)

### Step 7: Verify the File

You can verify your `.env` file has the correct format:

```powershell
Get-Content .env | Select-String "AZURE_CLIENT_SECRET"
```

It should show something like:
```
AZURE_CLIENT_SECRET=Z5l~abc123~XYZ789~SecretValue~Here
```

### Step 8: Restart Application

1. If your application is running, stop it (press `Ctrl+C` in the terminal)
2. Start it again:
   ```powershell
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. Try clicking "Refresh Index" again

## Important Notes

- **You can have multiple secrets active** - The old one will still work until it expires
- **The value is only shown once** - If you miss it, you'll need to create another one
- **Keep it secure** - Don't share this value or commit it to git
- **The .env file is in .gitignore** - So it won't be accidentally committed

## Troubleshooting

### "I missed copying the value"

Just create another new secret. You can have multiple secrets active at the same time.

### "The value is still hidden"

If you see "Hidden" or "***" in the Value column, it means you didn't copy it in time. Create a new secret.

### "I'm not sure if I copied the right thing"

The secret value:
- Starts with letters/numbers
- Contains tildes (~)
- Is quite long (usually 40+ characters)
- Looks like: `Z5l~abc123~XYZ789~SecretValue~Here`

The secret ID (which you DON'T want):
- Is a GUID with dashes
- Looks like: `467e4e93-dfe0-48d7-9a5d-697aeeb5b7b0`
- Is always visible in the list

## Visual Guide

When you create a new secret, you'll see:

```
┌─────────────────────────────────────────────────────────────┐
│ Client secrets                                              │
├─────────────────────────────────────────────────────────────┤
│ Description              Value              Expires          │
│ SharePoint Secret v2     Z5l~abc...~Here   24 months        │
│                          ↑                                    │
│                    COPY THIS IMMEDIATELY!                      │
│                    (It will disappear soon)                   │
└─────────────────────────────────────────────────────────────┘
```

After a few seconds, it will change to:

```
┌─────────────────────────────────────────────────────────────┐
│ Client secrets                                              │
├─────────────────────────────────────────────────────────────┤
│ Description              Value              Expires          │
│ SharePoint Secret v2     Hidden            24 months        │
│                          ↑                                    │
│                    Too late - create new one                 │
└─────────────────────────────────────────────────────────────┘
```

