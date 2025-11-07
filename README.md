# SharePoint Document Indexer

A lightweight, scalable web application that queries SharePoint via Microsoft Graph API to index and collate all files and folders. The application features async background processing, efficient caching, pagination, and is designed to integrate Meta Llama 3/3.1 for intelligent search capabilities.

## Features

- 🔍 **Complete SharePoint Indexing**: Automatically discovers and indexes all SharePoint sites, document libraries, folders, and files
- ⚡ **Async Processing**: Background task processing prevents request timeouts on large SharePoint instances
- 📄 **Pagination**: All endpoints support pagination for large datasets
- 💾 **Efficient Caching**: In-memory caching with TTL reduces redundant API calls
- 🔄 **Real-time Progress**: Track indexing progress with live updates
- 🔎 **Search**: Search files across all indexed SharePoint sites
- 📊 **Statistics Dashboard**: View total files, folders, size, and more
- 🎨 **Modern UI**: Clean, responsive web interface

## Technology Stack

- **Backend**: FastAPI (Python) - lightweight, async, excellent for API endpoints
- **Frontend**: HTML/JavaScript with modern UI
- **SharePoint Integration**: Microsoft Graph API (Python SDK)
- **Authentication**: Azure AD App Registration (Client Credentials)
- **Caching**: In-memory with cachetools for efficient memory management

## Prerequisites

- Python 3.8 or higher
- Office 365 account with SharePoint access
- Azure AD administrator access (to create app registration)

## Setup Instructions

### 1. Clone or Download the Repository

```bash
git clone <repository-url>
cd Document_Controlling
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Azure AD App Registration

You need to create an Azure AD App Registration to authenticate with Microsoft Graph API. This is **FREE** and takes about 5 minutes.

#### Step-by-Step:

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **"New registration"**
4. Fill in the details:
   - **Name**: SharePoint Document Indexer (or any name you prefer)
   - **Supported account types**: Accounts in this organizational directory only
   - Click **"Register"**
5. **Copy these values** (you'll need them):
   - **Application (client) ID** - Copy this value
   - **Directory (tenant) ID** - Copy this value
6. Go to **"Certificates & secrets"**:
   - Click **"New client secret"**
   - Add a description (e.g., "SharePoint Indexer Secret")
   - Choose expiration (recommended: 24 months)
   - Click **"Add"**
   - **IMPORTANT**: Copy the secret value immediately (you won't be able to see it again!)
7. Go to **"API permissions"**:
   - Click **"Add a permission"**
   - Select **"Microsoft Graph"**
   - Choose **"Application permissions"**
   - Add these permissions:
     - `Sites.Read.All` - Read all site collections
     - `Files.Read.All` - Read all files
   - Click **"Add permissions"**
8. **Grant admin consent**:
   - Click **"Grant admin consent for [Your Organization]"**
   - Confirm by clicking **"Yes"**

### 5. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   copy .env.example .env  # Windows
   # or
   cp .env.example .env    # Linux/Mac
   ```

2. Edit `.env` and fill in your Azure AD credentials:
   ```env
   AZURE_TENANT_ID=your-tenant-id-here
   AZURE_CLIENT_ID=your-client-id-here
   AZURE_CLIENT_SECRET=your-client-secret-here
   ```

3. Optional: Configure other settings:
   ```env
   # Optional: Specific SharePoint Site IDs (comma-separated)
   # Leave empty to auto-discover all sites
   SHAREPOINT_SITE_IDS=

   # Cache Settings
   CACHE_TTL_SECONDS=3600
   CACHE_MAX_SIZE=1000

   # Pagination Defaults
   DEFAULT_PAGE_SIZE=50
   MAX_PAGE_SIZE=500

   # Logging
   LOG_LEVEL=INFO

   # Server Settings
   HOST=0.0.0.0
   PORT=8000
   ```

### 6. Run the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be available at: `http://localhost:8000`

## Usage

1. **Open the Web Interface**: Navigate to `http://localhost:8000` in your browser

2. **Refresh Index**: Click the "Refresh Index" button to start indexing all SharePoint sites. This will:
   - Discover all SharePoint sites accessible to your app
   - Recursively index all document libraries, folders, and files
   - Build a searchable index

3. **View Statistics**: The dashboard shows:
   - Total sites indexed
   - Total files
   - Total folders
   - Total size

4. **Search Files**: Use the search bar to find files across all indexed SharePoint sites

5. **View Indexed Sites**: Browse the list of all indexed SharePoint sites with their statistics

## API Endpoints

- `GET /` - Serve frontend
- `POST /api/refresh` - Trigger SharePoint index refresh (async background task)
- `GET /api/status?job_id={job_id}` - Get indexing status/progress
- `GET /api/index?page={page}&limit={limit}` - Get current index structure (paginated)
- `GET /api/index/stats` - Get index statistics
- `GET /api/search?q={query}&page={page}&limit={limit}` - Search files (paginated)
- `GET /api/health` - Health check endpoint

## Architecture

### Backend Structure

- `app/main.py` - FastAPI application entry point
- `app/routes/sharepoint.py` - SharePoint API routes
- `app/services/sharepoint_service.py` - Microsoft Graph API integration
- `app/services/index_service.py` - Index management and caching
- `app/services/background_tasks.py` - Background job processing
- `app/models/index_models.py` - Data models
- `app/utils/logger.py` - Logging configuration
- `app/utils/pagination.py` - Pagination helpers
- `app/config.py` - Configuration management

### Frontend Structure

- `static/index.html` - Main UI
- `static/css/style.css` - Styling
- `static/js/app.js` - Frontend logic

## Scalability Features

- **Async Processing**: Background tasks prevent request timeouts
- **Pagination**: All endpoints support pagination for large datasets
- **Caching**: Efficient in-memory caching with TTL
- **Rate Limiting**: Respects Microsoft Graph API limits with intelligent backoff
- **Parallel Processing**: Concurrent requests for multiple sites/libraries
- **Memory Efficient**: Lazy loading and pagination prevent memory overflow

## Future Enhancements

- **Meta Llama 3/3.1 Integration**: Intelligent semantic search capabilities
- **File Content Extraction**: Extract and index file contents for full-text search
- **Vector Embeddings**: Store embeddings for semantic search
- **Incremental Updates**: Only refresh changed items
- **Export Functionality**: Export index to JSON/CSV

## Troubleshooting

### Authentication Errors

- Verify your Azure AD credentials in `.env`
- Ensure admin consent has been granted for API permissions
- Check that the client secret hasn't expired

### No Sites Found

- Verify your app has access to SharePoint sites
- Check that `Sites.Read.All` permission is granted
- Try specifying specific site IDs in `SHAREPOINT_SITE_IDS`

### Rate Limiting

- The application automatically handles rate limiting with exponential backoff
- For very large SharePoint instances, indexing may take time

## Cost Analysis

✅ **Everything is FREE:**

- FastAPI, Python, HTML/JavaScript - Free, open source
- Microsoft Graph API - FREE (included with Office 365 subscription)
- Azure AD App Registration - FREE (just configuration)
- No paid services required

## License

This project is provided as-is for internal use.

## Support

For issues or questions, please check the troubleshooting section or review the application logs.

#   d o c i n d e x  
 