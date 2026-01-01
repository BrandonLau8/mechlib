# mechlib

**Image metadata management system for mechanical parts and prototypes**

mechlib enables teams to upload images, embed custom metadata using ExifTool, store them in AWS S3, and perform semantic search using vector embeddings with PostgreSQL pgvector.

## Key Features

- **Custom Metadata Embedding**: Add rich metadata (brand, materials, mechanism, project) directly into image files using ExifTool custom XMP namespace
- **Semantic Search**: Find images using natural language queries via vector embeddings (OpenAI, Gemini, or local Ollama)
- **S3 Storage**: Scalable cloud storage with presigned URLs for secure access
- **MCP Server Integration**: Search your image library directly from Claude Desktop
- **React Frontend**: Office-based drag-and-drop upload interface with real-time processing
- **Cost-Effective**: ~$23/month production deployment using pgvector on AWS EC2

## Architecture

```
Office Network              AWS Cloud                Remote Access
┌─────────────┐            ┌──────────────┐         ┌─────────────┐
│  Frontend   │──API───────→│  FastAPI     │         │ MCP Server  │
│  (React)    │            │  Backend     │         │ (Claude)    │
└─────────────┘            │              │         └──────┬──────┘
                           │  PostgreSQL  │←───────────────┘
                           │  + pgvector  │         (semantic search)
                           │              │
                           │  S3 Storage  │
                           └──────────────┘
```

**Deployment Model:**
- **Upload/Process**: Office-only (local frontend, no cloud hosting needed)
- **Search**: Anywhere via MCP server in Claude Desktop
- **Backend**: EC2 with FastAPI, PostgreSQL + pgvector, S3

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ and npm/pnpm
- AWS account with S3 bucket configured
- OpenAI API key (or Gemini/Ollama for embeddings)

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/mechlib.git
   cd mechlib
   ```

2. **Configure environment:**
   ```bash
   cd backend
   cp .env.template .env
   # Edit .env with your AWS credentials, database config, and API keys
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

4. **Start frontend:**
   ```bash
   cd frontend
   npm install
   echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
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
2. Drag and drop images or click to upload
3. Fill in metadata (description, brand, materials, mechanism, project)
4. Click "Process Images" to embed metadata and upload to S3

### Semantic Search via MCP Server

Configure Claude Desktop to search your image library:

**Edit `~/.config/Claude/claude_desktop_config.json`:**
```json
{
  "mcpServers": {
    "mechlib": {
      "command": "python",
      "args": ["/path/to/mechlib/backend/mcp_server.py"],
      "env": {
        "PSQL_HOST": "localhost",
        "PSQL_PORT": "6432",
        "PSQL_DATABASE": "mechlib",
        "PSQL_USER": "your-username",
        "PSQL_PASSWORD": "your-password",
        "AWS_S3_BUCKET": "your-bucket-name",
        "AWS_REGION": "us-east-1",
        "OPENAI_API_KEY": "your-api-key"
      }
    }
  }
}
```

Then ask Claude: *"Search mechlib for plastic keyboard switches"*

## Production Deployment

Deploy to AWS EC2 for ~$23/month:

**Infrastructure:**
- EC2 t3.small instance with Docker + PostgreSQL + pgvector
- S3 bucket for images
- S3 bucket for database backups (90-day retention)
- Security groups (FastAPI restricted to office IP, PostgreSQL globally accessible for MCP)

**Deploy:**
```bash
cd terraform
terraform init
terraform apply

cd ..
./deploy.sh  # Push code and restart services on EC2
```

**Team Access:**
- Frontend runs locally in office (no cloud hosting needed)
- MCP server accessible remotely via SSH or direct database connection
- See `CLAUDE.md` for detailed team setup with SSH keys and access control

## Project Structure

```
mechlib/
├── backend/                 # Python backend
│   ├── src/
│   │   ├── mechlib/         # Core library (metadata, S3, vector store)
│   │   └── api/             # FastAPI REST API
│   ├── main.py              # CLI entry point
│   ├── mcp_server.py        # MCP server for Claude Desktop
│   └── config.py            # Configuration management
├── frontend/                # React frontend (Vite + TailwindCSS)
│   └── src/
│       ├── components/      # Upload, search, gallery components
│       └── App.tsx
├── terraform/               # AWS infrastructure as code
│   ├── ec2.tf
│   ├── s3-data.tf
│   └── security_groups.tf
└── docker/                  # Docker Compose for local dev
    └── compose.yaml
```

## Custom XMP Metadata

mechlib defines a custom XMP namespace (`mechlib`) for mechanical part metadata:

**Available tags:**
- `Materials`: Array of materials (e.g., ["Plastic", "Metal", "Aluminum"])
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
  -XMP-mechlib:Description="MX Red switch" \
  -overwrite_original \
  image.png
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
PSQL_PORT=6432
PSQL_DATABASE=mechlib
PSQL_USER=your-username
PSQL_PASSWORD=your-password

# Embedding Provider (openai, gemini, or ollama)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# API Keys
OPENAI_API_KEY=your-api-key
```

## Tech Stack

**Backend:**
- Python 3.12+ with `uv` package manager
- FastAPI for REST API
- PostgreSQL + pgvector for vector search
- LangChain for embeddings and document processing
- ExifTool for metadata embedding
- boto3 for S3 integration

**Frontend:**
- React 18 with Vite
- TailwindCSS for styling
- Axios for API calls
- React Dropzone for file uploads

**Infrastructure:**
- Docker & Docker Compose for local development
- Terraform for AWS infrastructure
- AWS EC2, S3, CloudWatch

## Documentation

- **[CLAUDE.md](./CLAUDE.md)**: Comprehensive developer guide and team deployment instructions
- **[docs/infrastructure_plan.md](./docs/infrastructure_plan.md)**: AWS production deployment guide
- **[docs/frontend_simplified.md](./docs/frontend_simplified.md)**: Frontend implementation details
- **[docs/setup_mcp.md](./docs/setup_mcp.md)**: MCP server configuration

## Development

**Run tests:**
```bash
cd backend
source .venv/bin/activate
pytest -v
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
npm run lint     # Lint code
```

## Team Deployment

For teams of 10+ users, mechlib supports:

- **EC2-based MCP server** with SSH remote access
- **Per-user SSH keys** for revokable access control
- **Claude Desktop integration** (works with Free, Pro, or Team tiers)
- **Phased rollout**: Start with free Claude accounts, upgrade heavy users as needed

**Estimated costs:**
- Infrastructure: $23/month (EC2 + S3 + backups)
- Claude accounts: $0-250/month depending on usage tier

See `CLAUDE.md` for detailed team setup instructions.

## Security

- Frontend: Office network only (no internet access)
- FastAPI: Restricted to office IP via AWS Security Groups
- PostgreSQL: Read-only user for MCP server (`mechlib_readonly`)
- S3: Presigned URLs with 1-hour expiration
- Credentials: Never committed to git (`.env` in `.gitignore`)

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

## Support

For issues and questions:
- Open an issue on GitHub
- See troubleshooting section in `CLAUDE.md`
- Check logs: `docker compose logs -f` or `/tmp/mechlib_mcp.log` for MCP server
