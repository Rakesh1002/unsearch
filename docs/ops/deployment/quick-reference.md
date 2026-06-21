# UnSearch Deployment - Quick Reference

Quick commands for deploying UnSearch on Digital Ocean.

## Prerequisites

- Digital Ocean droplet (Ubuntu 22.04)
- Domain name configured
- SSH access

---

## 1. Initial Server Setup (One-time)

```bash
# SSH into droplet
ssh root@your_droplet_ip

# Run automated setup
curl -fsSL https://raw.githubusercontent.com/your-org/unsearch/main/scripts/deploy-digitalocean.sh | sudo bash

# Or manually download and run
wget https://raw.githubusercontent.com/your-org/unsearch/main/scripts/deploy-digitalocean.sh
chmod +x deploy-digitalocean.sh
sudo ./deploy-digitalocean.sh
```

---

## 2. Clone Repository

```bash
# Switch to unsearch user
su - unsearch

# Clone repo
git clone https://github.com/your-org/unsearch.git
cd unsearch
```

---

## 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env

# Required variables:
# - SECRET_KEY (generate with: openssl rand -hex 32)
# - CLOUDFLARE_ACCOUNT_ID
# - CLOUDFLARE_API_TOKEN
# - STRIPE_SECRET_KEY (if billing enabled)
# - POSTHOG_API_KEY (if analytics enabled)
# - RESEND_API_KEY (if email enabled)
```

---

## 4. Obtain SSL Certificates

```bash
# Stop nginx if running
sudo docker compose down nginx 2>/dev/null || true

# Get certificates
sudo certbot certonly --standalone -d api.unsearch.dev
sudo certbot certonly --standalone -d unsearch.dev -d www.unsearch.dev

# Certificates stored in: /etc/letsencrypt/live/
```

---

## 5. Deploy Services

```bash
# Build images
docker compose build

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps
```

---

## 6. Initialize Database

```bash
# Run migrations
docker compose exec api alembic upgrade head

# Verify
docker compose exec api python -c "from app.models.database import SessionLocal; db = SessionLocal(); print('✓ Database connected')"
```

---

## 7. Configure Stripe (Optional)

```bash
# Install dependencies
pip install stripe python-dotenv

# Set Stripe key
export STRIPE_SECRET_KEY="sk_test_..."

# Create products
python scripts/setup_stripe.py

# Add price IDs to .env and restart
docker compose restart api
```

---

## 8. Verify Deployment

```bash
# Health check
curl https://api.unsearch.dev/health

# Test search
curl -X POST https://api.unsearch.dev/api/v1/agent/search \
  -H "X-API-Key: uns_test" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "max_results": 3}'

# Open docs
open https://api.unsearch.dev/docs

# Open web app
open https://unsearch.dev
```

---

## Common Commands

### View logs
```bash
docker compose logs -f              # All services
docker compose logs -f api          # API only
docker compose logs -f postgres     # Database only
```

### Restart services
```bash
docker compose restart              # All services
docker compose restart api          # API only
```

### Update code
```bash
git pull
docker compose build
docker compose up -d
docker compose exec api alembic upgrade head  # Run migrations
```

### Database backup
```bash
./backup-db.sh  # If backup script configured
```

### Check resource usage
```bash
docker stats                        # Container stats
free -h                             # System memory
df -h                               # Disk usage
```

---

## Troubleshooting

### Services won't start
```bash
docker compose logs <service>       # Check logs
docker compose restart <service>    # Restart
docker compose build --no-cache     # Rebuild
```

### Database issues
```bash
docker compose exec postgres psql -U unsearch  # Connect to DB
docker compose restart postgres                # Restart
```

### SSL certificate issues
```bash
sudo certbot renew --dry-run        # Test renewal
sudo certbot renew --force-renewal  # Force renewal
docker compose restart nginx        # Restart nginx
```

### Out of memory
```bash
docker system prune -a              # Clean up Docker
free -h                             # Check memory
docker stats                        # Check container usage
```

---

## Monitoring

### Check service health
```bash
curl https://api.unsearch.dev/health
```

### View metrics
```bash
curl https://api.unsearch.dev/metrics  # Prometheus metrics
```

### Check logs for errors
```bash
docker compose logs api | grep -i error
```

---

## Security

### Firewall status
```bash
sudo ufw status
```

### Check open ports
```bash
sudo netstat -tulpn | grep LISTEN
```

### Update system
```bash
sudo apt update && sudo apt upgrade -y
```

---

## Scaling

### Scale API workers
```bash
docker compose up -d --scale api=3
```

### Check container resources
```bash
docker stats
```

---

## Cost Reference

**Digital Ocean Droplet Costs:**
- Basic (2 vCPU, 4GB): $24/mo - Good for MVP
- General (4 vCPU, 8GB): $72/mo - Production
- Advanced (8 vCPU, 16GB): $144/mo - High traffic

**Total Monthly Cost (MVP):**
- Droplet: $24
- Domain: $1/mo ($12/year)
- **Total: ~$25/mo**

**Compare to alternatives:**
- Railway: $100+/mo
- Vercel + Supabase: $80+/mo
- AWS EC2 equivalent: $50+/mo

**UnSearch on DO = Best value**

---

## Support

**Documentation:**
- Full guide: `/docs/deployment-digitalocean.md`
- Quickstart: `/docs/quickstart.md`
- Environment: `/.env.example`

**Help:**
- Email: support@unsearch.dev
- Docs: docs.unsearch.dev
- Issues: github.com/your-org/unsearch/issues

---

## Deployment Checklist

- [ ] Droplet created (Ubuntu 22.04)
- [ ] DNS configured (api.unsearch.dev, unsearch.dev)
- [ ] Docker installed
- [ ] Repository cloned
- [ ] .env configured
- [ ] SSL certificates obtained
- [ ] Services deployed (docker compose up -d)
- [ ] Database migrated (alembic upgrade head)
- [ ] Health check passes
- [ ] Test API call successful
- [ ] Monitoring configured
- [ ] Backups scheduled
- [ ] Firewall enabled

---

**Ready to launch! 🚀**
