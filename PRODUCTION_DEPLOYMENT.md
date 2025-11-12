# Semantic Layer Platform - Production Deployment Guide

This guide covers production deployment of the complete AI-Native Semantic Layer Auto-Generation Platform.

## 🚀 Platform Overview

The semantic layer platform provides:

### Core Features
- **Semantic Layer Engine**: Multi-database metric and dimension definitions
- **AI Auto-Generation**: Automated YAML generation from warehouse metadata
- **Conversational Metrics**: Natural language query processing
- **Query Caching**: Multi-backend caching for performance
- **Visualization Engine**: Automated chart generation
- **Slack Integration**: Team collaboration through Slack bot
- **MCP Integration**: Claude Desktop integration
- **Production APIs**: REST API for external integrations

### Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Semantic Layer Platform                      │
├─────────────────────────────────────────────────────────────────┤
│  🤖 Claude Desktop    💬 Slack Bot     🌐 Web API             │
│  (MCP Server)         (Slack SDK)      (FastAPI)               │
├─────────────────────────────────────────────────────────────────┤
│  🗣️ Conversational    📊 Visualization  ⚡ Query Cache         │
│  Metrics             Engine            (Redis/Memory/File)      │
├─────────────────────────────────────────────────────────────────┤
│  🏗️ Semantic Layer    🔍 AI Inference   📝 YAML Generation     │
│  (Ibis Framework)    Engine            Engine                   │
├─────────────────────────────────────────────────────────────────┤
│  💾 Data Warehouses: Snowflake, BigQuery, DuckDB, PostgreSQL   │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

- **Docker & Docker Compose**: Container orchestration
- **Python 3.11+**: For local development
- **uv**: Fast Python package manager
- **Git**: Version control

### Optional Requirements
- **Redis**: For distributed caching
- **PostgreSQL**: For metadata storage
- **Slack Workspace**: For team integration
- **Claude Desktop**: For AI assistance

## 🛠️ Quick Start

### 1. Initial Setup

```bash
# Clone and setup
git clone <your-repo>
cd knowDB

# Setup environment (creates .env from template)
./deploy.sh setup

# Edit configuration
nano .env
```

### 2. Basic Deployment

```bash
# Start basic services (API + Redis cache)
./deploy.sh start

# Check status
./deploy.sh status

# View logs
./deploy.sh logs
```

### 3. Access Services

- **Web API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables (.env)

```bash
# === Core Configuration ===
SEMANTIC_MODELS_PATH=semantic_models/metrics.yml
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO

# === Security Configuration (REQUIRED) ===
# Generate secure API keys: openssl rand -base64 32
API_KEY_ADMIN=your-secure-admin-key-here
API_KEY_QUERY=your-secure-query-key-here
API_KEY_READ=your-secure-read-key-here
JWT_SECRET=your-jwt-secret-here            # openssl rand -base64 64
CORS_ORIGINS=https://yourdomain.com        # NO wildcards in production
ALLOWED_HOSTS=yourdomain.com,localhost

# === Database Connection ===
DATABASE_TYPE=duckdb  # duckdb, snowflake, bigquery, postgres
DATABASE_PATH=./data/sample.duckdb

# === Secure Database Credentials ===
POSTGRES_PASSWORD=your-secure-db-password
REDIS_PASSWORD=your-redis-password
GRAFANA_PASSWORD=your-grafana-admin-password

# === Caching ===
CACHE_BACKEND=redis  # memory, redis, file
CACHE_TTL=1800
REDIS_URL=redis://localhost:6379/0

# === Slack Integration ===
SLACK_ENABLED=true
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-secret

# === Features ===
ENABLE_WEB_API=true
ENABLE_VISUALIZATIONS=true
ENABLE_CONVERSATIONAL=true
```

### 🔐 Security Setup (CRITICAL)

**BEFORE PRODUCTION DEPLOYMENT:**

1. **Generate Secure API Keys:**
   ```bash
   # Generate admin API key
   echo "API_KEY_ADMIN=$(openssl rand -base64 32)" >> .env

   # Generate query API key
   echo "API_KEY_QUERY=$(openssl rand -base64 32)" >> .env

   # Generate read-only API key
   echo "API_KEY_READ=$(openssl rand -base64 32)" >> .env

   # Generate JWT secret
   echo "JWT_SECRET=$(openssl rand -base64 64)" >> .env
   ```

2. **Set Database Passwords:**
   ```bash
   # PostgreSQL password
   echo "POSTGRES_PASSWORD=$(openssl rand -base64 16)" >> .env

   # Redis password
   echo "REDIS_PASSWORD=$(openssl rand -base64 16)" >> .env

   # Grafana password
   echo "GRAFANA_PASSWORD=$(openssl rand -base64 16)" >> .env
   ```

3. **Configure CORS Origins:**
   ```bash
   # Replace with your actual domains
   echo "CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com" >> .env
   ```

4. **Set Trusted Hosts:**
   ```bash
   echo "ALLOWED_HOSTS=yourdomain.com,app.yourdomain.com" >> .env
   ```

### Database Configuration

#### Snowflake
```bash
DATABASE_TYPE=snowflake
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_USER=your-user
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_DATABASE=PROD_DB
SNOWFLAKE_WAREHOUSE=ANALYTICS_WH
```

#### BigQuery
```bash
DATABASE_TYPE=bigquery
BIGQUERY_PROJECT=your-project
BIGQUERY_CREDENTIALS_PATH=./credentials.json
```

#### PostgreSQL
```bash
DATABASE_TYPE=postgres
POSTGRES_HOST=your-host
POSTGRES_USER=your-user
POSTGRES_PASSWORD=your-password
POSTGRES_DATABASE=your-database
```

## 🐳 Docker Deployment

### Basic Services
```bash
# Start API + Redis
./deploy.sh start

# Or manually
docker-compose up -d
```

### With PostgreSQL
```bash
# Start with PostgreSQL for metadata
./deploy.sh start postgres

# Or manually
docker-compose --profile postgres up -d
```

### With Monitoring Stack
```bash
# Start with Prometheus + Grafana
./deploy.sh start monitoring

# Access Grafana at http://localhost:3000
# Default login: admin/admin
```

### With Reverse Proxy
```bash
# Start with Nginx reverse proxy
./deploy.sh start nginx

# Access via http://localhost (port 80)
```

## 🔍 Monitoring & Health Checks

### Health Endpoints

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/status

# Cache statistics
curl http://localhost:8000/cache/stats
```

### Service Status
```bash
# Check all services
./deploy.sh status

# View logs
./deploy.sh logs                # All services
./deploy.sh logs semantic-layer # Specific service
```

### Prometheus Metrics (with monitoring profile)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

## 🤖 Slack Bot Setup

### 1. Create Slack App
1. Go to https://api.slack.com/apps
2. Create new app "from scratch"
3. Add bot token scopes:
   - `app_mentions:read`
   - `chat:write`
   - `commands`
   - `channels:history`
   - `groups:history`
   - `im:history`

### 2. Configure Slash Commands
Add these slash commands in your Slack app:
- `/metrics` - List available metrics
- `/query` - Ask data questions
- `/dimensions` - List dimensions
- `/cache` - Cache management

### 3. Deploy Bot
```bash
# Configure in .env
SLACK_ENABLED=true
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-secret

# Restart services
./deploy.sh restart
```

### 4. Usage Examples
```
# In Slack
@semantic-bot show me total revenue by customer segment
/query What's our MRR growth this month?
/metrics
/cache stats
```

## 🖥️ Claude Desktop Integration

### MCP Server Setup
```json
{
  "mcpServers": {
    "semantic-layer": {
      "command": "python",
      "args": ["src/mcp_server.py"],
      "cwd": "/path/to/knowDB",
      "env": {
        "SEMANTIC_MODELS_PATH": "/path/to/knowDB/semantic_models/metrics.yml"
      }
    }
  }
}
```

### Usage in Claude Desktop
```
# Natural language queries
"Show me total revenue by customer segment"
"What are our top performing metrics?"
"Explain how MRR is calculated"
```

## 🌐 API Usage

### Authentication Required

All API endpoints (except `/health`) require authentication using API keys:

```bash
# Set your API key
export API_KEY="your-api-key-here"
```

### List Metrics
```bash
curl http://localhost:8000/metrics \
  -H "X-API-Key: REDACTED"
```

### Query Metrics
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: REDACTED" \
  -d '{
    "metric_name": "total_mrr",
    "dimensions": ["customer_segment"],
    "filters": ["customer_segment = \"Enterprise\""],
    "limit": 100
  }'
```

### List Dimensions
```bash
curl http://localhost:8000/dimensions \
  -H "X-API-Key: REDACTED"
```

### Cache Management (Admin Only)
```bash
# Get stats (read permission required)
curl http://localhost:8000/cache/stats \
  -H "X-API-Key: REDACTED"

# Clear cache (admin permission required)
curl -X POST http://localhost:8000/cache/clear \
  -H "X-API-Key: REDACTED"
```

### Permission Levels

- **Admin Key** (`API_KEY_ADMIN`): Full access to all operations
- **Query Key** (`API_KEY_QUERY`): Can read metrics and execute queries
- **Read Key** (`API_KEY_READ`): Can only list metrics and dimensions

## 🔧 Management Commands

### Deployment Script
```bash
./deploy.sh <command>

Commands:
  setup                 Setup environment and configuration
  build                 Build Docker images
  start [profile]       Start services
  stop                  Stop all services
  restart               Restart all services
  status                Show service status and health
  logs [service]        Show logs
  backup                Create backup
  update                Update deployment
  test                  Run tests
  cleanup               Clean up resources
```

### Backup & Recovery
```bash
# Create backup
./deploy.sh backup

# Backup includes:
# - semantic_models/
# - data/
# - .env configuration
```

### Updates
```bash
# Pull latest code and restart
./deploy.sh update

# Manual update
git pull origin main
./deploy.sh build
./deploy.sh restart
```

## 🔒 Security Considerations

### 🛡️ Production Security Checklist

**✅ IMPLEMENTED SECURITY CONTROLS:**
- [x] **Code Injection Prevention**: Replaced unsafe `eval()` with safe expression parser
- [x] **SQL Injection Protection**: Comprehensive input validation and sanitization
- [x] **Authentication & Authorization**: API key and JWT-based authentication with RBAC
- [x] **Rate Limiting**: Per-user query rate limiting to prevent abuse
- [x] **Input Validation**: Strict validation of all user inputs
- [x] **CORS Security**: Configurable, restrictive CORS policy
- [x] **Docker Security**: Non-root users, localhost-only database binds
- [x] **Security Headers**: All standard security headers implemented
- [x] **Audit Logging**: All queries logged with user attribution

**📋 PRODUCTION DEPLOYMENT CHECKLIST:**

**🔐 Authentication & Access Control**
- [ ] Generate strong API keys (32+ characters each)
- [ ] Set unique JWT secret (64+ characters)
- [ ] Configure restrictive CORS origins (no wildcards)
- [ ] Set trusted host whitelist
- [ ] Verify no default/weak passwords in use
- [ ] Test all permission levels work correctly

**🔒 Network Security**
- [ ] Enable HTTPS with TLS 1.3
- [ ] Configure firewall rules (allow only necessary ports)
- [ ] Use private networks for database connections
- [ ] Implement reverse proxy with rate limiting
- [ ] Configure DNS properly (no wildcards)

**🗄️ Database Security**
- [ ] Use strong database passwords (16+ characters)
- [ ] Enable database authentication (Redis AUTH, PostgreSQL auth)
- [ ] Configure database connection encryption
- [ ] Set up database access logging
- [ ] Implement database backup encryption

**📊 Monitoring & Alerting**
- [ ] Set up security event monitoring
- [ ] Configure failed authentication alerts
- [ ] Monitor for suspicious query patterns
- [ ] Set up rate limit violation alerts
- [ ] Implement log aggregation and analysis

**🔄 Updates & Maintenance**
- [ ] Regular security updates for all dependencies
- [ ] Automated vulnerability scanning
- [ ] Backup testing and restoration procedures
- [ ] Incident response plan documented
- [ ] Security contact information configured

### Environment Variables Security
```bash
# ⚠️ NEVER commit these to version control
API_KEY_ADMIN=$(openssl rand -base64 32)
API_KEY_QUERY=$(openssl rand -base64 32)
API_KEY_READ=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 64)

# Database security
POSTGRES_PASSWORD=$(openssl rand -base64 16)
REDIS_PASSWORD=$(openssl rand -base64 16)
GRAFANA_PASSWORD=$(openssl rand -base64 16)

# Network security
CORS_ORIGINS=https://yourdomain.com  # NEVER use * in production
ALLOWED_HOSTS=yourdomain.com
```

### 🚨 Security Incident Response

If you suspect a security breach:

1. **Immediate Actions:**
   ```bash
   # Rotate all API keys
   ./deploy.sh stop
   # Update .env with new keys
   ./deploy.sh start
   ```

2. **Investigation:**
   - Check application logs for suspicious activity
   - Review access patterns in monitoring systems
   - Examine database query logs

3. **Recovery:**
   - Reset all user credentials
   - Update security configurations
   - Apply security patches
   - Notify relevant stakeholders

### 🧪 Security Testing

Regular security testing should include:

```bash
# Test authentication
curl http://localhost:8000/metrics  # Should return 401

# Test authorization
curl -H "X-API-Key: REDACTED" -X POST http://localhost:8000/cache/clear  # Should return 403

# Test input validation
curl -H "X-API-Key: REDACTED" -X POST http://localhost:8000/query \
  -d '{"metric_name": "'; DROP TABLE users; --"}' # Should return 400

# Test rate limiting
for i in {1..100}; do curl -H "X-API-Key: REDACTED" http://localhost:8000/metrics; done
# Should eventually return 429
```

## 📊 Performance Optimization

### Caching Strategy
- **Memory Cache**: Fast, single-instance
- **Redis Cache**: Distributed, persistent
- **File Cache**: Disk-based, large datasets

### Database Optimization
- Use appropriate indexes
- Optimize query patterns
- Consider data partitioning
- Monitor query performance

### Scaling
- **Horizontal Scaling**: Multiple API instances
- **Load Balancing**: Nginx/HAProxy
- **Database Scaling**: Read replicas
- **Cache Scaling**: Redis cluster

## 🐛 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
./deploy.sh logs semantic-layer

# Check environment
docker-compose config

# Verify database connection
docker-compose exec semantic-layer python -c "from semantic_layer import SemanticLayer; sl = SemanticLayer('semantic_models/metrics.yml'); print('OK')"
```

#### Cache Issues
```bash
# Check Redis
docker-compose exec redis redis-cli ping

# Clear cache
curl -X POST http://localhost:8000/cache/clear

# Switch to memory cache
echo "CACHE_BACKEND=memory" >> .env
./deploy.sh restart
```

#### Slack Bot Not Responding
```bash
# Check bot logs
./deploy.sh logs semantic-layer | grep -i slack

# Verify tokens
echo $SLACK_BOT_TOKEN | cut -c1-10  # Should start with "xoxb-"

# Test bot health
curl http://localhost:8000/health
```

### Log Locations
- **Application Logs**: `docker-compose logs semantic-layer`
- **Cache Logs**: `docker-compose logs redis`
- **Access Logs**: `/app/logs/` (in container)

## 📞 Support & Maintenance

### Regular Maintenance
```bash
# Weekly backup
./deploy.sh backup

# Monthly cleanup
./deploy.sh cleanup

# Update dependencies
uv sync
./deploy.sh build
```

### Monitoring Checklist
- [ ] API response times
- [ ] Cache hit rates
- [ ] Database query performance
- [ ] Memory usage
- [ ] Disk space
- [ ] Error rates

## 🎉 Success!

Your semantic layer platform is now deployed and ready for production use!

### Next Steps
1. Configure your data warehouse connection
2. Set up semantic models in `semantic_models/metrics.yml`
3. Train your team on Slack commands
4. Integrate with Claude Desktop
5. Monitor performance and optimize

For support, check the logs and troubleshooting section above.