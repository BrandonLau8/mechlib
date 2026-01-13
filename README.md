# mechlib

**Image metadata management system for mechanical parts and prototypes**

mechlib enables teams to upload images, embed custom metadata using ExifTool, store them in AWS S3, and perform semantic search using vector embeddings with PostgreSQL pgvector.

## Key Features

- **Custom Metadata Embedding**: Add rich metadata (brand, materials, mechanism, project) directly into image files using ExifTool custom XMP namespace
- **Hybrid Search**: Combine keyword matching and semantic search for better results using PostgreSQL full-text search + vector embeddings
- **S3 Storage**: Scalable cloud storage with presigned URLs for secure access
- **React Frontend**: Drag-and-drop upload interface with real-time processing and search
- **REST API**: FastAPI backend with Google OAuth authentication
- **Cost-Effective**: ~$23/month production deployment using pgvector on AWS EC2

## Architecture

```
Office Network / Remote Access
┌─────────────────────────────┐
│  Frontend (React + Vite)    │
│  - Upload images            │
│  - Add metadata             │
│  - Search with hybrid mode  │
└──────────┬──────────────────┘
           │ HTTPS (REST API)
           ↓
┌─────────────────────────────┐
│  AWS EC2                    │
│  ┌─────────────────────┐   │
│  │  FastAPI Backend    │   │
│  │  - Image processing │   │
│  │  - Google OAuth     │   │
│  └──────┬──────────────┘   │
│         ↓                   │
│  ┌─────────────────────┐   │
│  │  PostgreSQL         │   │
│  │  + pgvector         │   │
│  │  + full-text search │   │
│  └─────────────────────┘   │
│         ↓                   │
│  ┌─────────────────────┐   │
│  │  S3 Storage         │   │
│  │  - Image files      │   │
│  │  - Presigned URLs   │   │
│  └─────────────────────┘   │
└─────────────────────────────┘
```

**Deployment Model:**
- **Frontend**: Can run locally (office) or be deployed to cloud
- **Backend**: EC2 with FastAPI, PostgreSQL + pgvector, S3
- **Search**: Hybrid keyword + semantic search via REST API
- **Auth**: Google OAuth 2.0 + JWT tokens

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ and npm
- AWS account with S3 bucket configured
- OpenAI API key (or Gemini/Ollama for embeddings)
- Google OAuth 2.0 credentials (for authentication)

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/mechlib.git
   cd mechlib
   ```

2. **Configure backend environment:**
   ```bash
   cd backend
   cp .env.template .env
   # Edit .env with your configuration:
   # - AWS credentials and S3 bucket
   # - PostgreSQL connection details
   # - OpenAI API key (or other embedding provider)
   # - Google OAuth client ID
   # - JWT secret key (generate with: openssl rand -hex 32)
   ```

3. **Start backend services with Docker Compose:**
   ```bash
   cd docker
   docker compose up -d
   ```
   This starts:
   - PostgreSQL + pgvector (port 5432)
   - pgbouncer connection pooling (port 6432)
   - FastAPI server (port 8000)

4. **Configure and start frontend:**
   ```bash
   cd frontend
   npm install

   # Create .env.local with API endpoint and Google OAuth client ID
   cat > .env.local << EOF
   VITE_API_BASE_URL=http://localhost:8000
   VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   EOF

   npm run dev
   ```
   Access at http://localhost:5173

### Manual Backend Setup (Alternative)

If you prefer not to use Docker Compose:

```bash
cd backend
uv sync  # Install dependencies (use uv, not pip)
source .venv/bin/activate

# Start FastAPI server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## Usage

### Upload and Process Images

1. Open the frontend at http://localhost:5173
2. Sign in with your Google account
3. Drag and drop images or click to upload
4. Fill in metadata:
   - **Description**: Detailed description of the part
   - **Brand**: Manufacturer name
   - **Materials**: Select applicable materials (Plastic, Metal, etc.)
   - **Process**: Manufacturing processes used
   - **Mechanism**: Type of mechanism (bayonet, threaded, snap-fit, etc.)
   - **Project**: Associated project name
5. Click "Process Images" to:
   - Embed metadata into image files using ExifTool
   - Upload to S3
   - Generate vector embeddings
   - Store in database for search

### Search Images

Use the search interface in the frontend:

1. Enter a natural language query (e.g., "red plastic keyboard switches")
2. Configure search parameters:
   - **Results (k)**: Number of results to return (default: 10)
   - **Score threshold**: Maximum distance (0.0-2.0, default: 0.5)
     - Lower = more strict, higher = more lenient
   - **Hybrid search**: Enable to combine keyword + semantic (recommended)
   - **Keyword weight**: Balance between keywords and semantics (0.0-1.0)
     - 0.5 = equal weight (recommended)
     - 1.0 = keyword only
     - 0.0 = semantic only
3. View results with images, metadata, and relevance scores

### API Endpoints

The FastAPI backend provides REST endpoints (see http://localhost:8000/docs for interactive docs):

- `POST /auth/google` - Authenticate with Google OAuth
- `POST /upload` - Upload images
- `POST /process` - Process images (embed metadata, upload to S3, add to vector DB)
- `POST /search` - Search images with hybrid search
- `PUT /update-metadata` - Update metadata for existing image
- `DELETE /delete-image` - Delete image from S3 and database

## Production Deployment

Deploy to AWS EC2 for ~$23/month:

**Infrastructure:**
- EC2 t3.small instance with Docker + PostgreSQL + pgvector
- S3 bucket for images
- S3 bucket for database backups (90-day retention)
- Security groups (restrict FastAPI to authorized IPs)

**Deploy with Terraform:**
```bash
cd terraform
terraform init
terraform plan
terraform apply

# Push code and restart services
cd ..
./deploy.sh
```

**Frontend Deployment Options:**
1. **Local only**: Run `npm run dev` in office (no hosting costs)
2. **Cloud hosting**: Build and deploy to S3 + CloudFront, Netlify, or Vercel

## Project Structure

```
mechlib/
├── backend/                 # Python backend
│   ├── src/
│   │   ├── mechlib/         # Core library
│   │   │   ├── metadata_fetcher.py
│   │   │   ├── img_fetcher.py
│   │   │   ├── img_processor.py
│   │   │   ├── s3_store.py
│   │   │   └── vector_store.py (hybrid search)
│   │   └── api/
│   │       ├── main.py      # FastAPI app
│   │       ├── auth.py      # Google OAuth + JWT
│   │       └── routers/     # API endpoints
│   ├── config.py            # Configuration management
│   ├── .ExifTool_config     # Custom XMP namespace
│   └── pyproject.toml       # Dependencies (use uv)
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   │   ├── ImageUploader.tsx
│   │   │   ├── MetadataForm.tsx
│   │   │   ├── SearchInterface.tsx
│   │   │   └── Login.tsx
│   │   ├── contexts/        # React context (auth)
│   │   ├── hooks/           # Custom hooks
│   │   └── lib/             # API client, types
│   └── package.json
├── terraform/               # AWS infrastructure as code
│   ├── ec2.tf
│   ├── s3-data.tf
│   ├── s3-backup.tf
│   └── security_groups.tf
└── docker/                  # Docker Compose for local dev
    └── compose.yaml
```

## Custom XMP Metadata

mechlib defines a custom XMP namespace (`mechlib`) for mechanical part metadata:

**Available tags:**
- `Materials`: Array of materials (e.g., ["Plastic", "Metal", "Aluminum"])
- `Process`: Manufacturing processes (e.g., ["Injection Molding", "CNC"])
- `Brand`: Manufacturer name
- `Project`: Associated project
- `Person`: Owner/uploader
- `Mechanism`: Type (e.g., "bayonet", "threaded", "snap-fit")
- `Description`: Detailed description
- `Timestamp`: When metadata was added

**Example ExifTool usage:**
```bash
cd backend
exiftool -config .ExifTool_config \
  -XMP-mechlib:Brand="Cherry" \
  -XMP-mechlib:Materials="Plastic" \
  -XMP-mechlib:Description="MX Red linear switch" \
  -XMP-mechlib:Mechanism="mechanical switch" \
  -overwrite_original \
  image.png

# Read metadata
exiftool -XMP-mechlib:all image.png
```

## Configuration

Environment variables (`.env` file in `backend/`):

```bash
# AWS S3
AWS_S3_BUCKET=your-bucket-name
AWS_PROFILE=default
AWS_REGION=us-east-1

# PostgreSQL (pgvector)
PSQL_HOST=localhost
PSQL_PORT=6432  # pgbouncer port (use 5432 for direct PostgreSQL)
PSQL_DATABASE=mechlib
PSQL_USER=your-username
PSQL_PASSWORD=your-password

# Embedding Provider (openai, gemini, or ollama)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# API Keys
OPENAI_API_KEY=your-api-key  # Required if using OpenAI

# Google OAuth (for frontend authentication)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

# JWT Configuration (for session management)
JWT_SECRET_KEY=your-secret-key  # Generate with: openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

**Frontend environment variables** (`.env.local` file in `frontend/`):

```bash
VITE_API_BASE_URL=http://localhost:8000  # or your EC2 IP/domain
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
```

## Hybrid Search System

mechlib uses **hybrid search** to combine keyword matching and semantic understanding:

**How it works:**
1. **Keyword Search**: PostgreSQL full-text search with GIN index
   - Searches across all metadata fields
   - Fast exact/partial word matching
   - Automatically updated via database triggers

2. **Semantic Search**: Vector embeddings with cosine similarity
   - Finds conceptually similar images
   - Works even with different terminology

3. **Hybrid Combination**: Merges both results
   - Keyword matches boost semantic scores
   - Configurable weighting (keyword_weight parameter)
   - Best of both approaches

**Why hybrid?**
- Pure keyword search misses conceptual matches
- Pure semantic search may miss exact term matches
- Hybrid provides precise keyword matching + conceptual similarity

## Tech Stack

**Backend:**
- Python 3.12+ with `uv` package manager
- FastAPI for REST API
- PostgreSQL + pgvector for vector search
- LangChain for embeddings and document processing
- ExifTool for metadata embedding
- boto3 for S3 integration
- Google Auth for OAuth verification
- PyJWT for token management

**Frontend:**
- React 18 with Vite
- TailwindCSS for styling
- Axios for API calls
- React Dropzone for file uploads
- React OAuth Google for authentication

**Infrastructure:**
- Docker & Docker Compose for local development
- Terraform for AWS infrastructure
- AWS EC2, S3, CloudWatch

## Development

**Run tests:**
```bash
cd backend
source .venv/bin/activate
pytest -v

# Run specific test
pytest test/test_vector_store.py -v
```

**Add dependencies:**
```bash
cd backend
uv add package-name  # Use uv, NOT pip
```

**Frontend development:**
```bash
cd frontend
npm run dev      # Development server
npm run build    # Production build
npm run preview  # Preview production build
npm run lint     # Lint code
```

**Database management:**
```bash
# Access PostgreSQL in Docker
docker exec -it mechlib-postgres psql -U mechlib -d mechlib

# View tables
\dt

# Inspect vector table
\d mechlib_images

# Check full-text search setup
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'mechlib_images' AND column_name = 'search_vector';
```

## Security

**Access Control:**
- FastAPI backend: Restrict to authorized IPs via AWS Security Groups
- Google OAuth: Only allow authorized Google accounts/domains
- JWT tokens: 24-hour expiration (configurable)
- All API endpoints require authentication

**Credentials:**
- `.env` files contain secrets and MUST NOT be committed (verify `.gitignore`)
- Use environment variables for all sensitive data
- AWS credentials configured via AWS profile (not hardcoded)
- JWT secret key must be strong (32+ random bytes)

**Data Protection:**
- S3 presigned URLs expire after 1 hour (configurable)
- CORS configured to allow only authorized origins
- Database passwords should be rotated regularly
- Use HTTPS in production (not HTTP)

## Google OAuth Setup

1. **Create OAuth 2.0 credentials** in Google Cloud Console:
   - Go to APIs & Services → Credentials
   - Create OAuth 2.0 Client ID (Web application)
   - Add authorized origins:
     - `http://localhost:5173` (development)
     - `https://yourdomain.com` (production)
   - Copy the Client ID

2. **Configure backend** (`.env`):
   ```bash
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   JWT_SECRET_KEY=your-secret-key  # Generate with: openssl rand -hex 32
   ```

3. **Configure frontend** (`.env.local`):
   ```bash
   VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   ```

## Troubleshooting

**Docker Compose fails to start:**
```bash
# Check if ports are in use
lsof -i :5432 :6432 :8000

# Reset and restart
cd docker
docker compose down -v
docker compose up -d
```

**Frontend can't connect to API:**
- Verify `VITE_API_BASE_URL` in frontend `.env.local`
- Check CORS settings in `backend/src/api/main.py`
- Ensure FastAPI is running: `curl http://localhost:8000/docs`

**Authentication errors:**
- Verify `GOOGLE_CLIENT_ID` matches in both backend and frontend `.env` files
- Check authorized origins in Google Cloud Console
- Ensure JWT_SECRET_KEY is set in backend `.env`
- Check browser console for specific error messages

**Search returns no results:**
- Verify images were successfully processed and uploaded
- Check database: `SELECT COUNT(*) FROM mechlib_images;`
- Try lowering `score_threshold` (e.g., 1.0 for lenient matching)
- Check logs: `docker compose logs -f api`

**ExifTool errors:**
- Ensure `exiftool` is installed: `exiftool -ver`
- Check config file exists: `backend/.ExifTool_config`
- Verify image files are valid (not corrupted)

## Cost Estimate

**AWS Infrastructure (~$23/month):**
- EC2 t3.small (24/7): ~$15/month
- S3 storage (100GB images): ~$2.30/month
- S3 backup storage: ~$5/month
- Data transfer: ~$1/month

**Additional Costs:**
- OpenAI API (embeddings): $0.0001 per 1K tokens (~$0.10 per 1000 images)
- CloudFront (if used): ~$1-5/month depending on traffic
- Frontend hosting (optional): $0 (local) or $0-10/month (Netlify/Vercel free tier)

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request with clear description

## Support

For issues and questions:
- Open an issue on GitHub
- Check logs:
  - Backend: `docker compose logs -f api`
  - Database: `docker compose logs -f postgres`
  - Frontend: Browser console
