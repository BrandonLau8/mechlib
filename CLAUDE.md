# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mechlib** is an image metadata management system for mechanical parts and prototypes. It enables teams to upload images, embed custom metadata using ExifTool, store them in AWS S3, and perform semantic search using vector embeddings with pgvector (PostgreSQL).

**Key Workflow**: Local image discovery → XMP metadata embedding → S3 upload → Vector embedding → Semantic search via MCP server

**Production Setup**: See `docs/infrastructure_plan.md` for AWS deployment guide (~$23/month using pgvector on EC2).

### Deployment Architecture

**Office-Only Upload/Process + Remote Search**

```
┌─────────────────────────────────────┐
│  OFFICE ONLY (Local Network)        │
│  Frontend (React + Vite)            │
│  - Upload images                     │
│  - Process metadata                  │
│  - Runs on: npm run dev             │
│  - No cloud hosting needed          │
│         ↓ API calls                  │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  AWS EC2 (Remote, Always Running)   │
│  - FastAPI backend (port 8000)      │
│  - PostgreSQL + pgvector            │
│  - S3 image storage                 │
│  - Accessible by office IP only     │
│         ↑                            │
└─────────────────────────────────────┘
                ↑
┌─────────────────────────────────────┐
│  REMOTE ACCESS (Anywhere)           │
│  MCP Server (Claude Desktop)        │
│  - Connects to EC2 database         │
│  - Semantic search                   │
│  - Read-only access                  │
└─────────────────────────────────────┘
```

**Use Cases:**
- **Upload/Process**: Office only (where physical parts are)
- **Search**: Anywhere via MCP server in Claude Desktop
- **Cost**: ~$23/month (no frontend hosting, no OAuth infrastructure)

## Team Deployment Setup

### Recommended Configuration for 10+ Users

**Architecture:** EC2-based MCP server with SSH remote access

**Why this approach:**
- ✅ Works from anywhere (home, office, travel)
- ✅ Credentials secured on EC2 (not distributed to 10+ computers)
- ✅ Easy maintenance (update code once on EC2)
- ✅ Per-user SSH keys (revokable access control)
- ✅ No local Python environment needed for users

### Claude Account Requirements

**Each team member needs:**
- Claude.ai account (free or paid)
- Claude Desktop app (free download from claude.ai)
- MCP servers work with all Claude tiers

**Account Tier Comparison:**

| Tier | Cost/User | Usage Limits | Best For |
|------|-----------|--------------|----------|
| **Free** | $0 | ~30-50 messages/day (~10-15 searches) | Light usage, testing |
| **Pro** | $20/month | ~10x higher limits | Individual heavy users |
| **Team** | $25/month* | Higher limits + admin controls | **Recommended for teams** |

*Minimum 5 seats, annual billing required

**Practical search capacity (Free tier):**
- Simple searches only: ~20 searches/day
- With follow-up questions: ~10-15 searches/day
- Mixed with other Claude usage: ~8-10 searches/day

### Recommended Phased Approach

**Phase 1: Start Free (Month 1)**
```
Cost: $23/month (infrastructure only)

- All users start with free Claude accounts
- Monitor who hits limits and how often
- Identify power users vs light users
```

**Phase 2: Targeted Upgrades (Month 2-3)**
```
Option A: Upgrade heavy users only
- 3 power users × $20 (Pro) = $60/month
- 7 light users × $0 (Free) = $0/month
Total: $83/month

Option B: Team plan (if 8+ users need Pro)
- 10 users × $25 (Team) = $250/month
- Centralized billing, admin controls
Total: $273/month
```

**Phase 3: Optimize (Ongoing)**
```
Monitor usage and adjust:
- Upgrade users who hit limits regularly
- Keep light users on free tier
- Consider Team plan when 8+ users need Pro
```

### Team Setup Instructions

#### One-Time EC2 Setup (Admin)

**1. Install mechlib on EC2:**
```bash
# SSH to EC2
ssh ubuntu@your-ec2-ip

# Install mechlib
sudo mkdir -p /opt/mechlib
sudo git clone https://github.com/your-org/mechlib.git /opt/mechlib
cd /opt/mechlib/backend
sudo uv sync

# Create MCP service user
sudo useradd -m -s /bin/bash mcp
sudo chown -R mcp:mcp /opt/mechlib

# Configure environment
sudo -u mcp cp /opt/mechlib/backend/.env.template /opt/mechlib/backend/.env
sudo -u mcp nano /opt/mechlib/backend/.env
# Fill in: PSQL_*, AWS_*, OPENAI_API_KEY, etc.
sudo chmod 600 /opt/mechlib/backend/.env
```

**2. Configure EC2 Security Group:**
```bash
# AWS Console → EC2 → Security Groups
# Add inbound rule:
Port 22 (SSH): 0.0.0.0/0  # For remote MCP access
# Or restrict to specific IPs for better security
```

**3. Set up SSH key authentication:**
```bash
# On EC2, as mcp user
sudo -u mcp mkdir -p /home/mcp/.ssh
sudo -u mcp chmod 700 /home/mcp/.ssh
sudo -u mcp touch /home/mcp/.ssh/authorized_keys
sudo -u mcp chmod 600 /home/mcp/.ssh/authorized_keys

# Disable password authentication (security best practice)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PubkeyAuthentication yes
sudo systemctl restart sshd
```

#### Per-User Setup (Each Team Member)

**1. Install Claude Desktop:**
- Download from claude.ai
- Create free Claude account (or upgrade to Pro later)

**2. Generate SSH key:**
```bash
# On user's computer
ssh-keygen -t ed25519 -f ~/.ssh/mechlib_mcp -N ""

# Display public key to send to admin
cat ~/.ssh/mechlib_mcp.pub
```

**3. Admin adds public key to EC2:**
```bash
# On EC2, as mcp user
sudo -u mcp nano /home/mcp/.ssh/authorized_keys
# Paste user's public key, save
```

**4. User configures SSH:**

Create/edit `~/.ssh/config`:
```
Host mechlib-mcp
    HostName YOUR_EC2_IP_HERE
    User mcp
    IdentityFile ~/.ssh/mechlib_mcp
    StrictHostKeyChecking no
```

**5. User configures Claude Desktop:**

Edit config file:
- **Mac/Linux:** `~/.config/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mechlib": {
      "command": "ssh",
      "args": [
        "mechlib-mcp",
        "/opt/mechlib/backend/.venv/bin/python",
        "/opt/mechlib/backend/mcp_server.py"
      ]
    }
  }
}
```

**6. Test connection:**
```bash
# Test SSH connection
ssh mechlib-mcp "echo 'Connection works!'"

# If successful, restart Claude Desktop
# Open Claude and ask: "Search mechlib for test images"
```

### Team Access Management

**Add new user:**
```bash
# User generates key and sends public key to admin
# Admin adds to EC2:
sudo -u mcp nano /home/mcp/.ssh/authorized_keys
# Append new public key
```

**Remove user access:**
```bash
# Admin removes their line from authorized_keys
sudo -u mcp nano /home/mcp/.ssh/authorized_keys
# Delete user's public key line, save
```

**Rotate credentials (quarterly):**
```bash
# Update EC2 .env file
sudo -u mcp nano /opt/mechlib/backend/.env
# Change: PSQL_PASSWORD, OPENAI_API_KEY, etc.
# No user config changes needed (credentials on server only)
```

### Cost Analysis for Teams

**Team of 10 people:**

| Component | Cost | Notes |
|-----------|------|-------|
| EC2 + PostgreSQL + S3 | $23/month | Infrastructure (fixed) |
| Claude Free (all users) | $0 | Limited to ~10-15 searches/day |
| Claude Pro (heavy users only) | $60-120/month | 3-6 users × $20 |
| Claude Team (all users) | $250/month | 10 users × $25, better for 8+ Pro users |

**Recommended starting point:** $23-83/month (infra + selective Pro upgrades)

**Scale to Team plan when:** 8+ users need Pro accounts ($250/month more cost-effective than 8+ × $20)

### Remote Access Notes

**Works from anywhere:**
- ✅ Home networks
- ✅ Coffee shops
- ✅ Travel/mobile hotspots
- ✅ Corporate VPNs

**No additional VPN needed** - SSH provides encrypted tunnel

**Latency:** 50-200ms depending on location (acceptable for search use case)

**Offline mode:** Not available (requires internet to reach EC2)

### Troubleshooting Team Setup

**SSH connection fails:**
```bash
# Test basic connectivity
ping your-ec2-ip

# Test SSH with verbose output
ssh -v mechlib-mcp

# Common issues:
# - EC2 security group doesn't allow port 22
# - SSH key permissions wrong: chmod 600 ~/.ssh/mechlib_mcp
# - Wrong user: should be 'mcp', not 'ubuntu' or 'ec2-user'
```

**MCP server not responding:**
```bash
# Check server logs
ssh mechlib-mcp "tail -f /tmp/mechlib_mcp.log"

# Test Python path
ssh mechlib-mcp "/opt/mechlib/backend/.venv/bin/python --version"

# Test MCP server directly
ssh mechlib-mcp "/opt/mechlib/backend/.venv/bin/python /opt/mechlib/backend/mcp_server.py"
```

**User hits Claude free tier limits:**
- Upgrade to Pro ($20/month) if hitting limits regularly (>2 days/week)
- Or wait until midnight PT when limits reset
- Monitor usage to determine if Pro is needed

## Repository Structure

```
mechlib/
├── backend/                          # Main application code
│   ├── main.py                       # CLI entry point
│   ├── mcp_server.py                 # MCP server for semantic search
│   ├── config.py                     # Centralized configuration
│   ├── .ExifTool_config              # Custom XMP namespace definition
│   ├── src/
│   │   ├── mechlib/                  # Core library package
│   │   │   ├── metadata_fetcher.py   # Metadata data class
│   │   │   ├── img_fetcher.py        # Local image discovery
│   │   │   ├── img_processor.py      # ExifTool metadata processing
│   │   │   ├── s3_store.py           # AWS S3 upload/presigned URLs
│   │   │   ├── vector_store.py       # pgvector integration (primary)
│   │   │   ├── pinecone_vector_store.py  # Pinecone (legacy)
│   │   │   └── gallery_generator.py  # HTML gallery generation
│   │   └── api/
│   │       └── main.py               # FastAPI REST API
│   ├── templates/
│   │   └── gallery.html              # Gallery template
│   └── pyproject.toml                # Dependencies (use uv, not pip)
├── frontend/                         # React frontend (office-only)
│   ├── src/
│   │   ├── components/               # React components
│   │   │   ├── ImageUploader.tsx     # Drag-and-drop upload
│   │   │   └── MetadataForm.tsx      # Metadata input form
│   │   ├── hooks/
│   │   │   └── useProcessImages.ts   # API integration
│   │   ├── lib/
│   │   │   ├── api.ts                # Axios client
│   │   │   └── types.ts              # TypeScript types
│   │   └── App.tsx                   # Main app component
│   ├── package.json                  # Node dependencies
│   └── vite.config.ts                # Vite configuration
├── terraform/                        # AWS infrastructure as code
│   ├── ec2.tf                        # EC2 for pgvector database
│   ├── s3-data.tf                    # S3 for images
│   ├── s3-backup.tf                  # S3 for database backups
│   └── security_groups.tf            # Network security
├── docs/                             # Documentation
│   ├── frontend_simplified.md        # Frontend implementation guide
│   └── ...                           # Other docs
└── mechlib_test/                     # Test images
```

## Development Commands

### Local Development with Docker Compose (Recommended)

**Quick Start:**
```bash
# Start all services (PostgreSQL + pgvector, pgbouncer, FastAPI)
cd docker
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down

# Stop and remove volumes (complete reset)
docker compose down -v
```

**Prerequisites:**
- Docker and Docker Compose installed
- `.env` file in `backend/` directory (copy from `backend/.env.template`)
- AWS credentials configured (`~/.aws/credentials`)

**Services:**
- **PostgreSQL + pgvector**: Port 5432 (internal only)
- **pgbouncer**: Port 6432 (connection pooling, use this from apps)
- **FastAPI**: Port 8000 (API server)

### Manual Backend Setup (Alternative)

**Backend:**
```bash
# Install dependencies (use uv, NOT pip)
cd backend
uv sync

# Install with optional dependencies
uv sync --extra cli    # Interactive CLI prompts
uv sync --extra dev    # Development/testing tools
uv sync --all-extras   # All optional features

# Activate virtual environment
source .venv/bin/activate

# Create .env file from template
cp .env.template .env
# Edit .env with your configuration
```

**Frontend:**
```bash
# Install dependencies
cd frontend
npm install

# Create .env.local for API endpoint
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
# For production: echo "VITE_API_BASE_URL=http://your-ec2-ip:8000" > .env.local
```

### Running the Application

**Option 1: Docker Compose (Recommended for Local Dev):**
```bash
# Start all services
cd docker
docker compose up -d

# Frontend (separate terminal)
cd frontend
npm run dev
# Access at http://localhost:5173
```

**Option 2: Manual (for CLI workflow or debugging):**
```bash
# Frontend
cd frontend
npm run dev
# Access at http://localhost:5173
# Office team accesses at http://YOUR_IP:5173

# Backend - CLI workflow (full pipeline)
cd backend
source .venv/bin/activate
python main.py

# Backend - FastAPI server (for frontend)
cd backend
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
# --host 0.0.0.0 allows network access (required for frontend)

# Backend - MCP server (semantic search, remote access)
cd backend
source .venv/bin/activate
python mcp_server.py
# Note: Logs to /tmp/mechlib_mcp.log (stdio used for MCP protocol)
```

### Frontend Build & Lint

```bash
cd frontend

# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

### Testing

```bash
# With Docker Compose running
cd backend
source .venv/bin/activate
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test/test_specific.py -v
```

### ExifTool Operations

```bash
# Write custom metadata (from project root)
cd backend
exiftool -config .ExifTool_config \
  -XMP-mechlib:Brand="Cherry" \
  -XMP-mechlib:Materials="Plastic" \
  -XMP-mechlib:Description="Mechanical keyboard switch" \
  -overwrite_original \
  ../mechlib_test/image.png

# Read custom metadata
exiftool -XMP-mechlib:all ../mechlib_test/image.png
```

### Infrastructure & Deployment

```bash
# Initialize Terraform
cd terraform
terraform init

# Plan infrastructure changes
terraform plan

# Apply infrastructure
terraform apply

# Deploy application to EC2
cd ..
./deploy.sh

# SSH to EC2 instance
./ssh_to_ec2.sh

# Manual database backup
./backup.sh
```

## Architecture & Key Concepts

### Core Data Flow

```
User Input → ImageFetcher → ImageProcessor → S3_StoreManager → ImageProcessor → VectorStoreManager
(path)       (Metadata[])    (XMP embed)     (S3 upload)        (Documents)    (pgvector)
```

1. **ImageFetcher.add_path()**: Discover images, create `Metadata` objects
2. **ImageProcessor.metadata_to_imgs()**: Embed XMP metadata via ExifTool subprocess
3. **S3_StoreManager.add_files()**: Upload to S3, return `{filename: s3_uri}` dict
4. **ImageProcessor.s3_uris_to_metadata()**: Link S3 URIs to Metadata objects
5. **ImageProcessor.make_documents()**: Convert to LangChain Documents
6. **VectorStoreManager.add_documents()**: Store in pgvector for semantic search

### Core Classes

**Metadata** (`metadata_fetcher.py`):
- Data class for image metadata (filename, description, brand, materials, etc.)
- Methods: `from_dict()`, `to_dict()`, `from_terminal()` (interactive CLI)
- Required fields: `filename`, `description`, `person`

**ImageProcessor** (`img_processor.py`):
- Uses **subprocess** to call ExifTool CLI for writing metadata (not Python wrapper)
- Uses **pyexiftool.ExifToolHelper** for reading metadata
- Config file: `backend/.ExifTool_config`

**VectorStoreManager** (`vector_store.py`):
- Primary: pgvector (PostgreSQL extension) via langchain-postgres
- Legacy: Pinecone (code exists, being phased out)
- Returns presigned S3 URLs in search results

### Custom XMP Namespace

Namespace: `mechlib` (URI: `http://mechlib.com/ns/1.0/`)

**Tags**:
- Materials (array): e.g., ["Plastic", "Metal", "Aluminum"]
- Brand: Manufacturer name
- Project: Associated project
- Person: Username/owner
- Mechanism: Type (e.g., "bayonet", "threaded", "snap-fit")
- Description: Detailed description
- Timestamp: When metadata was added

### Configuration System

Environment variables (`.env` file in `backend/`):

```bash
# AWS S3
AWS_S3_BUCKET=<bucket-name>
AWS_PROFILE=<profile-name>
AWS_REGION=us-east-1

# PostgreSQL (pgvector)
PSQL_HOST=localhost  # or EC2 IP for production
PSQL_PORT=6432       # pgbouncer port (use 5432 for direct PostgreSQL)
PSQL_DATABASE=mechlib
PSQL_USER=<username>
PSQL_PASSWORD=<password>

# Embedding Provider
EMBEDDING_PROVIDER=openai  # or: ollama, gemini
EMBEDDING_MODEL=text-embedding-3-small  # or: nomic-embed-text, text-embedding-004

# API Keys (based on provider)
OPENAI_API_KEY=<key>   # Only if using openai
GEMINI_API_KEY=<key>   # Only if using gemini

# LangSmith (optional)
LANGSMITH_API_KEY=<key>
LANGSMITH_TRACING=false
```

**Embedding Providers** (pluggable):
- `ollama`: Local embeddings, nomic-embed-text (768 dims)
- `gemini`: Google text-embedding-004 (768 dims)
- `openai`: OpenAI text-embedding-3-small (1536 dims) - **recommended for production**

**Config class** (`config.py`):
- Singleton: `config = Config()`
- Builds PostgreSQL connection string: `postgresql+psycopg://user:pass@host:port/db`
- Initializes embedding models on-demand
- Returns embedding dimensions for each provider

### Vector Database Strategy

**Development**: Pinecone (free tier, easy setup)
**Production**: pgvector on AWS EC2 (cost-effective, multi-user ready)

**Why pgvector**:
- ✅ ~$23/month vs $70/month for Pinecone
- ✅ Multi-user support via pgbouncer connection pooling
- ✅ Store vectors + metadata in same database
- ✅ Perfect for 1k-100k vectors
- ✅ Daily automated backups to S3

### MCP Server

**Purpose**: Exposes semantic image search as MCP tool for Claude Desktop

**Tool**: `search_images(query, k=3, score_threshold=0.7)`
- Searches pgvector database
- Filters results by similarity score
- Generates HTML gallery with presigned S3 URLs
- Returns path to `gallery.html`

**Logging**: Uses file logging (`/tmp/mechlib_mcp.log`) to avoid stdio interference

**Remote Access Configuration**:
Users configure Claude Desktop to connect to EC2 database in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mechlib": {
      "command": "python",
      "args": ["/path/to/mechlib/backend/mcp_server.py"],
      "env": {
        "PSQL_HOST": "your-ec2-ip.amazonaws.com",
        "PSQL_PORT": "5432",
        "PSQL_DATABASE": "mechlib",
        "PSQL_USER": "mechlib_readonly",
        "PSQL_PASSWORD": "secure-password",
        "AWS_S3_BUCKET": "mechlib-images",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

**Security**: MCP uses read-only database user (`mechlib_readonly`) with SELECT privileges only

### S3 Integration

**Image Storage** (`mechlib-images` bucket):
- Directory-based organization
- Presigned URLs for temporary access (default: 1 hour)
- Content type and disposition set for browser viewing

**Backup Storage** (`mechlib-backups` bucket):
- Daily pg_dump backups (cron: 2AM)
- 90-day retention lifecycle policy
- Automated via EC2 cron job

### Docker Compose Architecture

**Local Development Stack** (`docker/compose.yaml`):

```
Frontend (npm run dev)
    ↓ HTTP :8000
mechlib-api (FastAPI container)
    ↓ PostgreSQL :6432
mechlib-pgbouncer (connection pooling)
    ↓ :5432 (internal)
mechlib-postgres (pgvector container)
    ↓
mechlib_postgres_data (persistent volume)
```

**Key Features**:
- **Network isolation**: All services in `mechlib-network` bridge network
- **Data persistence**: Named volume `mechlib_postgres_data` survives container restarts
- **Connection pooling**: pgbouncer handles 100 client connections with 20 PostgreSQL connections
- **Auto-reload**: FastAPI container watches for code changes
- **AWS credentials**: Mounted read-only from `~/.aws`

**Service Details**:
- `postgres`: pgvector/pgvector:0.8.1-pg17, runs init.sql on first start
- `pgbouncer`: edoburu/pgbouncer, exposes port 6432 to host
- `api`: Built from `backend/Dockerfile`, exposes port 8000 to host

## Important Implementation Details

### Path Handling
- Uses `pathlib.Path` throughout
- All image paths are absolute
- Project root: `config.project_root` (backend directory)

### ExifTool Integration
- **Write**: subprocess call to exiftool CLI (proven reliable)
- **Read**: pyexiftool.ExifToolHelper wrapper
- Always uses `-overwrite_original` flag
- Tag extraction: splits on `:` to handle namespace prefixes

### Metadata Document Structure

LangChain Documents created by `ImageProcessor.make_documents()`:

```python
Document(
    page_content="<description> Tags: [filename:..., brand:..., materials:..., ...]",
    metadata={
        'filename': 'image_name',
        'description': 'Detailed description',
        'brand': 'Brand name',
        'materials': ['Plastic', 'Metal'],
        'mechanism': 'Switch type',
        'project': 'Project name',
        'person': 'Username',
        'timestamp': '2024:11:28 12:00:00 EST',
        's3_url': 'https://bucket.s3.amazonaws.com/...'
    }
)
```

### Production Deployment

**Infrastructure**:
- EC2 t3.small instance running Docker pgvector
- FastAPI backend accessible from office IP only
- PostgreSQL accessible globally (for MCP server)
- CloudWatch for monitoring and logs
- Secrets Manager for credentials
- Daily backups to S3 via cron

**Frontend Deployment**:
- **NOT** deployed to cloud (runs locally in office)
- No hosting costs, no authentication needed
- Office network security = access control

**Cost Breakdown** (~$23/month):
- EC2 (t3.small): ~$8/month
- S3 storage (100GB): ~$2.30/month
- Backup retention: ~$13/month
- Data transfer: ~$0.05/month
- **Frontend hosting**: $0 (local)
- **No ALB needed**: Saves $16/month
- **No OAuth infrastructure**: Saves complexity

**Deployment**:
- Backend: Run `./deploy.sh` to push code and restart services on EC2
- Frontend: `npm run dev` on office computer (or any team member's machine)

## Dependency Management

**CRITICAL**: Use `uv`, NOT `pip`

```bash
# Add dependency
uv add package-name

# Remove dependency
uv remove package-name

# Sync from pyproject.toml
uv sync
```

**Key Dependencies**:
- `boto3`: AWS S3 integration
- `pyexiftool`: Metadata reading (requires system `exiftool` binary)
- `langchain-*`: Document processing, embeddings (core, google-genai, ollama, postgres, openai)
- `psycopg[binary]`: PostgreSQL adapter
- `langchain-postgres`: pgvector integration
- `pillow`: Image validation
- `fastmcp`: MCP server
- `fastapi[standard]`: REST API server
- `questionary`: Interactive CLI (optional: `cli` group)
- `pytest`: Testing (optional: `dev` group)

**System Dependencies** (required on host or in Docker):
- `exiftool`: Perl-based metadata tool (installed via apt/brew)

## Current Project State

**Completed**:
- ✅ CLI workflow fully functional
- ✅ MCP server with semantic search (remote access)
- ✅ pgvector integration (langchain-postgres)
- ✅ S3 upload and presigned URLs
- ✅ ExifTool custom XMP namespace
- ✅ Terraform infrastructure code
- ✅ FastAPI REST API (upload and process endpoints)
- ✅ Comprehensive documentation

**Recently Completed**:
- ✅ React frontend (office-only deployment)
  - Single-page app with upload + metadata form
  - Drag-and-drop image upload using react-dropzone
  - Material selection with checkboxes
  - Real-time processing status
  - Built with Vite + React + TailwindCSS
- ✅ Docker Compose local development environment
  - PostgreSQL + pgvector container
  - pgbouncer connection pooling
  - FastAPI container with auto-reload

**Legacy/Deprecated**:
- Pinecone integration (transitioning to pgvector)

## Known Patterns

### Interactive CLI Inputs

Uses `questionary` for user prompts:

```python
# Path selection with autocomplete
path = questionary.path("Where is your image path?",
                       complete_style=CompleteStyle.MULTI_COLUMN).ask()

# Form with multiple fields
answers = questionary.form(
    description=questionary.text('Description: ', multiline=True),
    materials=questionary.checkbox('Materials: ', choices=[...])
).ask()
```

### Error Handling

Methods return boolean or empty lists on failure:

```python
def add_metadata(self, path_list: list[Path]) -> bool:
    try:
        # ... operations
        return True
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return False
```

### Logging

All modules use standard logging:

```python
logger = logging.getLogger(__name__)
```

Main application configures in `main.py`:

```python
logging.basicConfig(level=logging.INFO)
```

## Security Notes

**Access Control**:
- **Frontend**: Office network only (no internet access)
- **FastAPI Backend**: Restricted to office IP via AWS Security Groups
- **PostgreSQL**: Open for MCP server access (read-only user recommended)
- **CORS**: Configured to allow office IP only

**Credentials**:
- `.env` file contains API keys and MUST NOT be committed
- `.mcp.json` file contains credentials and MUST NOT be committed (verify in `.gitignore`)
- Verify `.gitignore` includes `.env` and `.mcp.json`
- Production uses AWS Secrets Manager (not .env files on EC2)
- MCP server uses read-only database user (`mechlib_readonly`)
- **CRITICAL**: Never commit API keys or passwords to git

**Data Protection**:
- S3 presigned URLs expire after 1 hour (configurable)
- AWS credentials configured via AWS profile (not hardcoded)
- EC2 security groups enforce network-level restrictions

**Security Group Configuration**:
```hcl
# FastAPI: Office IP only
ingress {
  from_port   = 8000
  to_port     = 8000
  protocol    = "tcp"
  cidr_blocks = ["YOUR_OFFICE_IP/32"]
}

# PostgreSQL: Global (for MCP server)
ingress {
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
}
```

## Recent Major Changes

**December 2024 Package Restructuring & Architecture**:
- Files moved to `backend/` directory
- Source organized as proper Python package: `src/mechlib/`
- `Metadata` class introduced for structured data handling
- `ImageFetcher` now manages `Metadata` objects (not just paths)
- Switched from Pinecone to pgvector for production
- Added MCP server for semantic search (remote access)
- FastAPI REST API with upload and process endpoints
- **Architecture decision**: Office-local frontend + EC2 backend model
  - Frontend runs locally (no cloud hosting needed)
  - Upload/process in office only
  - Search via MCP server from anywhere
  - Cost-effective: ~$23/month (no ALB, no OAuth)

## Troubleshooting

### Common Issues

**Docker Compose fails to start:**
```bash
# Check if ports are already in use
lsof -i :5432  # PostgreSQL
lsof -i :6432  # pgbouncer
lsof -i :8000  # FastAPI

# Reset everything
cd docker
docker compose down -v
docker compose up -d
```

**Frontend can't connect to API:**
- Verify `.env.local` has correct `VITE_API_BASE_URL`
- Check CORS settings in `backend/src/api/main.py`
- Ensure FastAPI is running: `curl http://localhost:8000/docs`

**Database connection errors:**
- Use port `6432` (pgbouncer), not `5432` (direct PostgreSQL)
- Check `.env` file has correct `PSQL_*` variables
- Verify Docker network: `docker network inspect mechlib-network`

**ExifTool errors:**
- Ensure `exiftool` is installed: `exiftool -ver`
- Check config file exists: `backend/.ExifTool_config`
- Verify working directory is `backend/` when running

**MCP server not responding:**
- Check logs: `tail -f /tmp/mechlib_mcp.log`
- Verify `.mcp.json` configuration in Claude Desktop
- Ensure database is accessible from MCP server

**S3 upload failures:**
- Verify AWS credentials: `aws s3 ls` (using profile from `.env`)
- Check bucket permissions
- Ensure `AWS_PROFILE`, `AWS_S3_BUCKET`, and `AWS_REGION` are set

## Additional Resources

- **docs/infrastructure_plan.md**: Complete production deployment guide with AWS setup
- **docs/frontend_simplified.md**: Frontend implementation guide (office-local deployment)
- **docs/setup_mcp.md**: MCP server configuration and Claude Desktop integration
- **docs/aws_setup.md**: AWS credentials and S3 bucket setup instructions
- **docker/compose.yaml**: Docker Compose configuration for local development
