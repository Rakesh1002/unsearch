# Digital Ocean Droplet Deployment Guide

Deploy UnSearch to Digital Ocean droplet using Docker Compose.

## Prerequisites

- Digital Ocean account
- Domain name (unsearch.dev)
- SSH access to your droplet

## Droplet Specifications

### Recommended Specifications:

**For MVP (< 1000 users):**
- **Size:** Basic - $24/mo
  - 2 vCPUs
  - 4 GB RAM
  - 80 GB SSD
  - 4 TB transfer

**For Production (1000+ users):**
- **Size:** General Purpose - $72/mo
  - 4 vCPUs
  - 8 GB RAM
  - 160 GB SSD
  - 5 TB transfer

**Configuration:**
- **OS:** Ubuntu 22.04 LTS
- **Location:** Choose closest to your users
- **Firewall:** Enable (ports 80, 443, 22)

---

## Step 1: Create Digital Ocean Droplet

### Via Dashboard:

1. Go to [DigitalOcean Dashboard](https://cloud.digitalocean.com)
2. Click "Create" → "Droplets"
3. Choose Ubuntu 22.04 LTS
4. Select droplet size (Basic $24/mo recommended for MVP)
5. Choose datacenter region
6. Add SSH key (required)
7. Create droplet

### Via CLI (doctl):

```bash
# Install doctl
brew install doctl  # macOS
# or: snap install doctl  # Linux

# Authenticate
doctl auth init

# Create droplet
doctl compute droplet create unsearch-api \
  --size s-2vcpu-4gb \
  --image ubuntu-22-04-x64 \
  --region nyc1 \
  --ssh-keys <your-ssh-key-id> \
  --enable-monitoring \
  --enable-ipv6 \
  --tag-names production,unsearch
```

---

## Step 2: Initial Server Setup

SSH into your droplet:

```bash
ssh root@your_droplet_ip
```

### Update system:

```bash
apt update && apt upgrade -y
```

### Install Docker:

```bash
# Install dependencies
apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
apt install -y docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

### Create non-root user (recommended):

```bash
adduser unsearch
usermod -aG sudo unsearch
usermod -aG docker unsearch

# Copy SSH keys
rsync --archive --chown=unsearch:unsearch ~/.ssh /home/unsearch

# Switch to new user
su - unsearch
```

---

## Step 3: Clone and Configure Project

### Clone repository:

```bash
cd /home/unsearch
git clone https://github.com/your-org/unsearch.git
cd unsearch
```

### Create production environment file:

```bash
cp .env.example .env
nano .env
```

**Required variables:**

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY="<run: openssl rand -hex 32>"

# Database (will be created by Docker Compose)
DATABASE_URL=postgresql://unsearch:<YOUR_DB_PASSWORD>@postgres:5432/unsearch
REDIS_URL=redis://redis:6379

# Internal services
SEARXNG_URL=http://searxng:8080

# Security
ALLOWED_ORIGINS=https://unsearch.dev,https://www.unsearch.dev
CORS_CREDENTIALS=true

# Cloudflare Workers AI
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_API_TOKEN=your_api_token
CLOUDFLARE_AI_ENABLED=true

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_UNS_PRO_PRICE_ID=price_...
STRIPE_UNS_GROWTH_PRICE_ID=price_...
STRIPE_UNS_SCALE_PRICE_ID=price_...

# Analytics
POSTHOG_API_KEY=phc_...
POSTHOG_HOST=https://app.posthog.com

# Email
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@unsearch.dev

# Monitoring
SENTRY_DSN=https://...@sentry.io/...

# Production URLs
API_URL=https://api.unsearch.dev
WEB_URL=https://unsearch.dev
```

### Generate secure SECRET_KEY:

```bash
openssl rand -hex 32
# Copy output to .env as SECRET_KEY
```

---

## Step 4: Configure SSL with Let's Encrypt

### Install Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Obtain SSL certificates:

```bash
# For API subdomain
sudo certbot certonly --standalone -d api.unsearch.dev

# For main domain
sudo certbot certonly --standalone -d unsearch.dev -d www.unsearch.dev

# Certificates will be in: /etc/letsencrypt/live/
```

### Update Nginx configuration:

Edit `/root/unsearch/nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
    limit_req_zone $binary_remote_addr zone=web_limit:10m rate=50r/s;

    # API Server (api.unsearch.dev)
    server {
        listen 80;
        server_name api.unsearch.dev;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name api.unsearch.dev;

        ssl_certificate /etc/letsencrypt/live/api.unsearch.dev/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/api.unsearch.dev/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        client_max_body_size 10M;

        location / {
            limit_req zone=api_limit burst=20 nodelay;

            proxy_pass http://api:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }

    # Web App (unsearch.dev)
    server {
        listen 80;
        server_name unsearch.dev www.unsearch.dev;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name unsearch.dev www.unsearch.dev;

        ssl_certificate /etc/letsencrypt/live/unsearch.dev/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/unsearch.dev/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        location / {
            limit_req zone=web_limit burst=10 nodelay;

            proxy_pass http://web:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### Update docker-compose.yml for SSL:

Edit nginx service in `docker-compose.yml`:

```yaml
nginx:
  image: nginx:alpine
  container_name: unsearch-nginx
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro  # ← Add SSL certificates
  depends_on:
    - api
    - web
  networks:
    - unsearch-net
  restart: unless-stopped
```

---

## Step 5: Configure DNS

Point your domains to the droplet IP:

### At your DNS provider (e.g., Cloudflare, Namecheap):

```
Type: A
Name: api
Value: <your_droplet_ip>
TTL: 300

Type: A
Name: @
Value: <your_droplet_ip>
TTL: 300

Type: A
Name: www
Value: <your_droplet_ip>
TTL: 300
```

### Verify DNS propagation:

```bash
dig api.unsearch.dev +short
dig unsearch.dev +short
# Should return your droplet IP
```

---

## Step 6: Deploy with Docker Compose

### Build and start all services:

```bash
cd /home/unsearch/unsearch

# Build images
docker compose build

# Start services in background
docker compose up -d

# View logs
docker compose logs -f

# Check service status
docker compose ps
```

### Initialize database:

```bash
# Run migrations
docker compose exec api alembic upgrade head

# Verify database connection
docker compose exec api python -c "from app.models.database import SessionLocal; db = SessionLocal(); print('Database connected')"
```

---

## Step 7: Configure Firewall

### Using UFW (Uncomplicated Firewall):

```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status

# Output should show:
# 22/tcp   ALLOW   Anywhere
# 80/tcp   ALLOW   Anywhere
# 443/tcp  ALLOW   Anywhere
```

---

## Step 8: Set Up Automatic SSL Renewal

### Create renewal script:

```bash
sudo nano /etc/cron.weekly/renew-ssl
```

Add:

```bash
#!/bin/bash
certbot renew --quiet --deploy-hook "docker compose -f /home/unsearch/unsearch/docker-compose.yml restart nginx"
```

Make executable:

```bash
sudo chmod +x /etc/cron.weekly/renew-ssl
```

---

## Step 9: Verify Deployment

### Health checks:

```bash
# API health
curl https://api.unsearch.dev/health

# API docs
open https://api.unsearch.dev/docs

# Web app
open https://unsearch.dev

# Test search endpoint
curl -X POST https://api.unsearch.dev/api/v1/agent/search \
  -H "X-API-Key: uns_test" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "max_results": 3}'
```

### Check services:

```bash
# Check all containers are running
docker compose ps

# View logs
docker compose logs api
docker compose logs web
docker compose logs searxng
docker compose logs postgres
docker compose logs redis

# Check resource usage
docker stats
```

---

## Step 10: Set Up Monitoring

### Install monitoring tools:

```bash
# Install node_exporter for Prometheus
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.7.0.linux-amd64.tar.gz
sudo cp node_exporter-1.7.0.linux-amd64/node_exporter /usr/local/bin/
rm -rf node_exporter-1.7.0.linux-amd64*

# Create systemd service
sudo nano /etc/systemd/system/node_exporter.service
```

Add:

```ini
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=unsearch
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter
```

### Set up log rotation:

```bash
sudo nano /etc/logrotate.d/unsearch
```

Add:

```
/home/unsearch/unsearch/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 unsearch unsearch
    sharedscripts
    postrotate
        docker compose -f /home/unsearch/unsearch/docker-compose.yml restart api
    endscript
}
```

---

## Backup Strategy

### Database backups:

Create backup script:

```bash
nano /home/unsearch/backup-db.sh
```

Add:

```bash
#!/bin/bash
BACKUP_DIR="/home/unsearch/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker compose exec -T postgres pg_dump -U unsearch unsearch | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_$DATE.sql.gz"
```

Make executable and schedule:

```bash
chmod +x /home/unsearch/backup-db.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/unsearch/backup-db.sh
```

---

## Scaling & Performance

### Horizontal Scaling:

To scale API workers:

```bash
# Edit docker-compose.yml
docker compose up -d --scale api=3
```

### Vertical Scaling:

Resize droplet:
1. Go to Digital Ocean Dashboard
2. Select droplet → Resize
3. Choose larger size
4. Restart droplet

### Database Optimization:

```bash
# Edit PostgreSQL config for production
docker compose exec postgres bash

# Inside container:
nano /var/lib/postgresql/data/postgresql.conf

# Increase:
# shared_buffers = 1GB
# effective_cache_size = 3GB
# max_connections = 200

# Restart PostgreSQL
docker compose restart postgres
```

---

## Troubleshooting

### Services won't start:

```bash
# Check logs
docker compose logs <service_name>

# Restart specific service
docker compose restart api

# Rebuild if needed
docker compose build --no-cache api
docker compose up -d
```

### High memory usage:

```bash
# Check memory
free -h

# Check container usage
docker stats

# Restart containers
docker compose restart
```

### Database connection errors:

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Connect to database
docker compose exec postgres psql -U unsearch

# Check connections
docker compose exec postgres psql -U unsearch -c "SELECT * FROM pg_stat_activity;"
```

### SSL certificate issues:

```bash
# Test certificate renewal
sudo certbot renew --dry-run

# Force renewal
sudo certbot renew --force-renewal

# Restart nginx
docker compose restart nginx
```

---

## Security Best Practices

- [ ] Use strong passwords for database
- [ ] Enable UFW firewall
- [ ] Keep system updated (apt update && apt upgrade)
- [ ] Use SSH keys (disable password auth)
- [ ] Enable automatic security updates
- [ ] Regular database backups
- [ ] Monitor logs for suspicious activity
- [ ] Use environment variables for secrets
- [ ] Enable rate limiting in Nginx
- [ ] Set up fail2ban for SSH protection

---

## Cost Estimation

**Digital Ocean Droplet:**
- Basic ($24/mo): 2 vCPU, 4GB RAM - Good for MVP
- General Purpose ($72/mo): 4 vCPU, 8GB RAM - Production ready

**Additional costs:**
- Domain: $12/year
- Backups (optional): $4.80/mo (20% of droplet cost)
- Monitoring (optional): Free (self-hosted Prometheus/Grafana)

**Total Monthly Cost:**
- MVP: $24-28/mo
- Production: $72-80/mo

Compare to Railway: $100+/mo for equivalent

---

## Next Steps

1. ✅ Create droplet
2. ✅ Install Docker
3. ✅ Configure SSL
4. ✅ Deploy with Docker Compose
5. ✅ Set up monitoring
6. ✅ Configure backups
7. **Test end-to-end**
8. **Launch to beta users**

---

## Support

- Digital Ocean Docs: https://docs.digitalocean.com
- Docker Docs: https://docs.docker.com
- UnSearch Support: support@unsearch.dev

---

**Ready to deploy!** 🚀

All configurations are in place. Just follow the steps above to deploy on your Digital Ocean droplet.
