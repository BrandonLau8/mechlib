# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mechlib** is an image metadata management system for mechanical parts and prototypes. It enables teams to upload images, embed custom metadata using ExifTool, store them in AWS S3, and perform semantic search using vector embeddings with pgvector (PostgreSQL).

**Key Workflow**: Local image discovery → XMP metadata embedding → S3 upload → Vector embedding → Semantic search via MCP server

**Production Setup**: See `backend/CLAUDE.md` for detailed architecture and `infrastructure_plan.md` for AWS deployment guide (~$23/month using pgvector on EC2).

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
│   │       └── main.py               # FastAPI REST API (partial)
│   ├── templates/
│   │   └── gallery.html              # Gallery template
│   └── pyproject.toml                # Dependencies (use uv, not pip)
├── terraform/                        # AWS infrastructure as code
│   ├── ec2.tf                        # EC2 for pgvector database
│   ├── s3-data.tf                    # S3 for images
│   ├── s3-backup.tf                  # S3 for database backups
│   └── security_groups.tf            # Network security
└── mechlib_test/                     # Test images
```

## Development Commands

### Environment Setup

```bash
# Install dependencies (use uv, NOT pip)
uv sync

# Install with optional dependencies
uv sync --extra cli    # Interactive CLI prompts
uv sync --extra mcp    # MCP server support
uv sync --extra api    # FastAPI server
uv sync --all-extras   # All optional features

# Activate virtual environment
source .venv/bin/activate
```

### Running the Application

```bash
# CLI workflow (full pipeline)
cd backend
python main.py

# MCP server (semantic search)
cd backend
python mcp_server.py
# Note: Logs to /tmp/mechlib_mcp.log (stdio used for MCP protocol)

# FastAPI server (optional, partial implementation)
cd backend
uv run fastapi dev src/api/main.py
# or: uvicorn src.api.main:app --reload
```

### Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v
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
PSQL_HOST=<hostname>
PSQL_PORT=5432
PSQL_DATABASE=mechlib
PSQL_USER=<username>
PSQL_PASSWORD=<password>

# Embedding Provider
EMBEDDING_PROVIDER=ollama  # or gemini
EMBEDDING_MODEL=nomic-embed-text  # or text-embedding-004
GEMINI_API_KEY=<key>  # Only if using gemini

# LangSmith (optional)
LANGSMITH_API_KEY=<key>
LANGSMITH_TRACING=true
```

**Embedding Providers** (pluggable):
- `ollama`: Local embeddings, nomic-embed-text (768 dims)
- `gemini`: Google text-embedding-004 (768 dims)
- Infrastructure plan uses OpenAI text-embedding-3-small (1536 dims) for production

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

### S3 Integration

**Image Storage** (`mechlib-images` bucket):
- Directory-based organization
- Presigned URLs for temporary access (default: 1 hour)
- Content type and disposition set for browser viewing

**Backup Storage** (`mechlib-backups` bucket):
- Daily pg_dump backups (cron: 2AM)
- 90-day retention lifecycle policy
- Automated via EC2 cron job

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
- pgbouncer for multi-user connection pooling (port 6432)
- CloudWatch for monitoring and logs
- Secrets Manager for credentials
- Daily backups to S3 via cron

**Cost Breakdown** (~$23/month):
- EC2 (t3.small): ~$8/month
- S3 storage (100GB): ~$2.30/month
- Backup retention: ~$13/month
- Data transfer: ~$0.05/month

**Deployment**: Run `./deploy.sh` to push code and restart services on EC2

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
- `pyexiftool`: Metadata reading
- `langchain-*`: Document processing, embeddings (core, google-genai, ollama, postgres)
- `psycopg[binary]`: PostgreSQL adapter
- `langchain-postgres`: pgvector integration
- `pillow`: Image validation
- `fastmcp`: MCP server (optional: `mcp` group)
- `questionary`: Interactive CLI (optional: `cli` group)
- `fastapi`: REST API (optional: `api` group)

## Current Project State

**Completed**:
- ✅ CLI workflow fully functional
- ✅ MCP server with semantic search
- ✅ pgvector integration (langchain-postgres)
- ✅ S3 upload and presigned URLs
- ✅ ExifTool custom XMP namespace
- ✅ Terraform infrastructure code
- ✅ Comprehensive documentation

**Partial**:
- 🚧 FastAPI REST API (basic endpoints, incomplete)

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

- `.env` file contains API keys and MUST NOT be committed
- Verify `.gitignore` includes `.env`
- S3 presigned URLs expire after 1 hour (configurable)
- AWS credentials configured via AWS profile (not hardcoded)
- EC2 security groups restrict database access

## Recent Major Changes

**December 2024 Package Restructuring**:
- Files moved to `backend/` directory
- Source organized as proper Python package: `src/mechlib/`
- `Metadata` class introduced for structured data handling
- `ImageFetcher` now manages `Metadata` objects (not just paths)
- Switched from Pinecone to pgvector for production
- Added MCP server for semantic search
- FastAPI endpoints started (partial implementation)

## Additional Resources

- **backend/CLAUDE.md**: Detailed architecture, class references, workflow diagrams
- **infrastructure_plan.md**: Complete production deployment guide with AWS setup
- **setup_mcp.md**: MCP server configuration and Claude Desktop integration
- **aws_setup.md**: AWS credentials and S3 bucket setup instructions
