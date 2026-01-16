![ME/CFS Database Manager](header_image.png)

# ME/CFS Database Manager

A web-based database management application for ME/CFS (Myalgic Encephalomyelitis/Chronic Fatigue Syndrome) patient data. This tool manages clinical and assay data storage in MongoDB and enables export of data in formats compatible with RTI's mapMECFS system.

## Features

- **Data Import**
  - Clinical data from Excel spreadsheets
  - Biospecimen tracking data
  - Assay data (proteomics, cytokines, metabolomics, miRNA-seq, scRNA-seq, etc.)

- **Data Export**
  - Binned demographic summaries with configurable formats
  - RTI-compatible exports (phenotype and assay data TSV files)

- **Data Viewing**
  - Browse clinical records
  - Search biospecimen data
  - View imported assay metadata

- **Web Interface**
  - Modern Gradio-based UI accessible via browser
  - User authentication
  - Drag-and-drop file uploads

## Usage Guide

### Logging In

1. Open the application in your browser
2. Select your user account from the dropdown
3. Click "Login"

### Importing Data

#### Clinical Data
1. Go to **Import Data** > **Clinical Data**
2. Upload an Excel file (.xlsx or .xls) containing clinical data
3. Required column: `study_id`
4. Click "Import Clinical Data"

#### Biospecimen Data
1. Go to **Import Data** > **Biospecimen Data**
2. Upload an Excel file with biospecimen tracking information
3. Required column: `specimen_id`
4. Click "Import Biospecimen Data"

#### Assay Data
1. Go to **Import Data** > **Assay Data**
2. Upload an Excel file with two sheets:
   - **Metadata**: Assay configuration (assay type, biospecimen type, etc.)
   - **Data Table**: The actual assay measurements
3. Review the parsed metadata
4. Click "Import Assay Data"

### Exporting Data

#### Binned Summary Export
1. Go to **Export Data** > **Binned Summary**
2. Select export format (Full, Minimum, Keller, SC Paper)
3. Click "Generate Export"
4. Download the TSV file

#### RTI Export
1. Go to **Export Data** > **Export for RTI**
2. Upload an assay configuration Excel file
3. Review the configuration preview
4. Click "Generate RTI Export"
5. Download both:
   - Phenotype TSV file
   - Assay data TSV file

### Viewing Data

- **Clinical Data**: Browse all clinical records in a table format
- **Biospecimen Data**: Search and filter biospecimen records

## Prerequisites

### For Local Development
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- MongoDB 7.0+ (running locally or in Docker)

### For Docker Deployment
- Docker
- Docker Compose (optional, for simplified deployment)

## Quick Start (Local Development)

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/MECFS.git
cd MECFS
```

### 2. Install Dependencies
```bash
uv sync
```

### 3. Start MongoDB
You can run MongoDB locally or via Docker:
```bash
# Using Docker
docker run -d --name mongodb -p 27017:27017 mongo:7.0
```

### 4. Run the Application
```bash
uv run python -m src.mecfs_ui.app
```

The application will be available at: **http://localhost:7861**

## Docker Deployment

### Option A: Using Docker Compose (Recommended)

```bash
cd docker
docker-compose up -d --build
```

This starts both MongoDB and the application. Access at: **http://your-server:7861**

**Useful commands:**
```bash
# View logs
docker-compose logs -f app
docker-compose logs -f mongodb

# Stop containers
docker-compose down

# Rebuild after code changes (preserves database)
docker-compose up -d --build app
```

### Option B: Manual Docker Setup (For Restricted Environments)

For environments with Docker restrictions (e.g., HPC clusters), run containers manually:

**1. Create a Docker network**
```bash
# Standard environments
docker network create mecfs-network

# BioHPC Cornell (use your username prefix)
docker network create <username>__biohpc_mecfs
```

**2. Create data directory for MongoDB**
```bash
mkdir -p ~/mecfs_data/mongodb
```

**3. Start MongoDB**
```bash
docker run -d \
  --name mecfs-mongodb \
  --network mecfs-network \
  -v ~/mecfs_data/mongodb:/data/db \
  -p 27017:27017 \
  mongo:7.0
```

**4. Build and run the application**
```bash
cd MECFS
docker build -t mecfs-app -f docker/Dockerfile .

docker run -d \
  --name mecfs-app \
  --network mecfs-network \
  -e MONGO_HOST=mecfs-mongodb \
  -e MONGO_PORT=27017 \
  -p 7861:7861 \
  mecfs-app
```

**5. Verify containers are running**
```bash
docker ps | grep mecfs
docker logs mecfs-app
```

### Option C: Cornell BioHPC Deployment

For Cornell BioHPC clusters, use the `docker1` command and follow these specific steps:

**1. Create a Docker network with your username prefix**
```bash
docker1 network create <username>__biohpc_mecfs
```

**2. Create data directory for MongoDB**
```bash
mkdir -p /workdir/<username>/mecfs_data/mongodb
```

**3. Start MongoDB**
```bash
docker1 run -d \
  --name mecfs-mongodb \
  --network <username>__biohpc_mecfs \
  -v /workdir/<username>/mecfs_data/mongodb:/data/db \
  -p 27017:27017 \
  mongo:7.0
```

**4. Get MongoDB container's IP address**

Due to BioHPC network restrictions, you may need to use the container's IP address instead of hostname:
```bash
docker1 inspect mecfs-mongodb | grep IPAddress
```

Note the IP address (e.g., `172.19.0.2`).

**5. Build the application image**
```bash
cd /workdir/<username>/path/to/MECFS
docker1 build -t biohpc_<username>/mecfs-app -f docker/Dockerfile .
```

**6. Run the application**

Use the MongoDB IP address from step 4:
```bash
docker1 run -d \
  --name mecfs-app \
  --network <username>__biohpc_mecfs \
  -e MONGO_HOST=<MONGODB_IP_ADDRESS> \
  -e MONGO_PORT=27017 \
  -p 7861:7861 \
  biohpc_<username>/mecfs-app
```

**7. Verify containers are running**
```bash
docker1 ps | grep mecfs
docker1 logs mecfs-app
```

**8. Access the application**

The application will be available at: `http://<biohpc-server>:7861`

**Stopping and restarting containers:**
```bash
# Stop containers
docker1 stop mecfs-app mecfs-mongodb

# Remove containers (data persists in the mounted directory)
docker1 rm mecfs-app mecfs-mongodb

# Restart by repeating steps 3-6
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_HOST` | `localhost` | MongoDB hostname |
| `MONGO_PORT` | `27017` | MongoDB port |
| `PORT` | `7861` | Application web server port |

### Database

The application uses MongoDB with the database name `mecfs_db_consolidated_assays` by default. This can be configured in `set_up_globals.py`.

## Project Structure

```
MECFS/
├── src/
│   └── mecfs_ui/
│       ├── app.py              # Main Gradio application
│       └── components/
│           ├── auth.py         # User authentication
│           ├── import_tabs.py  # Data import UI
│           ├── export_tabs.py  # Data export UI
│           ├── query_tabs.py   # Data viewing UI
│           └── file_handlers.py # Excel file processing
├── data/
│   ├── mongo_setup.py          # MongoDB connection
│   └── clinical_data.py        # Data models
├── services/
│   └── data_service.py         # Database operations
├── docker/
│   ├── Dockerfile              # Application container
│   └── docker-compose.yml      # Multi-container setup
├── set_up_globals.py           # Global configuration
├── utilities.py                # Utility functions
└── pyproject.toml              # Python dependencies
```

## Data Persistence

- **Docker Compose**: Data persists in Docker volumes (`mongodb_data`, `mongodb_config`)
- **Manual Docker**: Data persists in the mounted directory (e.g., `~/mecfs_data/mongodb`)
- **Local Development**: Data persists in your local MongoDB installation

To backup MongoDB data:
```bash
docker exec mecfs-mongodb mongodump --out /data/backup
docker cp mecfs-mongodb:/data/backup ./mongodb_backup
```

## Troubleshooting

### Cannot connect to MongoDB
- Ensure MongoDB container is running: `docker ps | grep mongodb`
- Check MongoDB logs: `docker logs mecfs-mongodb`
- Verify network connectivity between containers

### Port already in use
- Change the port via environment variable: `-e PORT=7862`
- Or modify `docker-compose.yml` / `app.py`

### Container can't resolve hostname
- Ensure both containers are on the same Docker network
- Use `docker network inspect <network-name>` to verify

### BioHPC/HPC-specific issues
- Use network names with your username prefix
- Use local directory mounts instead of named volumes
- Contact your HPC support for specific Docker restrictions

## Development

### Running Tests
```bash
uv run pytest tests/
```

### Code Style
The project follows standard Python conventions. Use `uv` for all package management:
```bash
uv add <package>      # Add dependency
uv run <command>      # Run commands in virtual environment
```

## License

[Add your license information here]

## Contact

Genomics Innovation Hub, Cornell University

For BioHPC support: support@biohpc.cornell.edu
