# UnSearch API Deployment Guide

This guide covers various deployment options for the UnSearch API, from development to production environments.

## 🚀 Quick Start (Development)

### Prerequisites

- Python 3.11+
- Redis server
- PostgreSQL database
- SearXNG instance

### Setup

```bash
# Clone and setup
git clone <repository-url>
cd UnSearch
make setup

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start services
make docker-up

# Run migrations
make migrate

# Start development server
make dev
```

## 🐳 Docker Deployment

### Local Development with Docker

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Production Docker Setup

1. **Build production image:**

```bash
make docker-build
```

2. **Configure production environment:**

Create `docker-compose.prod.yml`:

```yaml
version: "3.8"
services:
  api:
    image: UnSearch/api:latest
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - API_KEYS=${API_KEYS}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SEARXNG_URL=${SEARXNG_URL}
    ports:
      - "8000:8000"
    restart: unless-stopped
    depends_on:
      - postgres
      - redis
      - searxng

  worker:
    image: UnSearch/api:latest
    command: celery -A app.workers.tasks worker --loglevel=info
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    restart: unless-stopped
    depends_on:
      - postgres
      - redis

  flower:
    image: UnSearch/api:latest
    command: celery -A app.workers.tasks flower
    ports:
      - "5555:5555"
    environment:
      - REDIS_URL=${REDIS_URL}
    restart: unless-stopped
    depends_on:
      - redis

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=UnSearch
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  searxng:
    image: searxng/searxng:latest
    ports:
      - "8080:8080"
    volumes:
      - ./searxng:/etc/searxng:rw
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

3. **Deploy:**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## ☸️ Kubernetes Deployment

### Prerequisites

- Kubernetes cluster
- kubectl configured
- Helm (optional)

### 1. Create Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: UnSearch
```

### 2. ConfigMap and Secrets

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: UnSearch-config
  namespace: UnSearch
data:
  ENVIRONMENT: "production"
  DEBUG: "false"
  SEARXNG_URL: "http://searxng:8080"
  REDIS_URL: "redis://redis:6379"

---
apiVersion: v1
kind: Secret
metadata:
  name: UnSearch-secrets
  namespace: UnSearch
type: Opaque
data:
  DATABASE_URL: <base64-encoded-database-url>
  API_KEYS: <base64-encoded-api-keys>
```

### 3. Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: UnSearch-api
  namespace: UnSearch
spec:
  replicas: 3
  selector:
    matchLabels:
      app: UnSearch-api
  template:
    metadata:
      labels:
        app: UnSearch-api
    spec:
      containers:
        - name: api
          image: UnSearch/api:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: UnSearch-secrets
                  key: DATABASE_URL
            - name: API_KEYS
              valueFrom:
                secretKeyRef:
                  name: UnSearch-secrets
                  key: API_KEYS
          envFrom:
            - configMapRef:
                name: UnSearch-config
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
```

### 4. Service and Ingress

```yaml
apiVersion: v1
kind: Service
metadata:
  name: UnSearch-api-service
  namespace: UnSearch
spec:
  selector:
    app: UnSearch-api
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: UnSearch-ingress
  namespace: UnSearch
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - api.UnSearch.com
      secretName: UnSearch-tls
  rules:
    - host: api.UnSearch.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: UnSearch-api-service
                port:
                  number: 80
```

## 🌐 Cloud Deployments

### AWS ECS

1. **Create task definition:**

```json
{
  "family": "UnSearch-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "UnSearch-api",
      "image": "your-account.dkr.ecr.region.amazonaws.com/UnSearch-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:ssm:region:account:parameter/UnSearch/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/UnSearch-api",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

2. **Create service:**

```bash
aws ecs create-service \
  --cluster UnSearch-cluster \
  --service-name UnSearch-api \
  --task-definition UnSearch-api:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

### Google Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT-ID/UnSearch-api

# Deploy
gcloud run deploy UnSearch-api \
  --image gcr.io/PROJECT-ID/UnSearch-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="DATABASE_URL=projects/PROJECT-ID/secrets/database-url:latest"
```

### Azure Container Instances

```bash
# Create resource group
az group create --name UnSearch-rg --location eastus

# Deploy container
az container create \
  --resource-group UnSearch-rg \
  --name UnSearch-api \
  --image UnSearch/api:latest \
  --dns-name-label UnSearch-api \
  --ports 8000 \
  --environment-variables 'ENVIRONMENT'='production' \
  --secure-environment-variables 'DATABASE_URL'='your-database-url'
```

## 🔧 Production Configuration

### Environment Variables

Key production settings:

```bash
# Security
ENVIRONMENT=production
DEBUG=false
API_KEYS=key1,key2,key3
ALLOWED_ORIGINS=https://yourdomain.com

# Performance
WORKERS=4
SCRAPING_MAX_CONCURRENT=20
CACHE_DEFAULT_TTL=3600

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://host:6379
REDIS_MAX_CONNECTIONS=50

# Rate Limiting
RATE_LIMIT_DEFAULT=100/hour
RATE_LIMIT_BURST=200

# Monitoring
ENABLE_METRICS=true
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### SSL/TLS Configuration

For production, always use HTTPS:

1. **Nginx SSL configuration:**

```nginx
server {
    listen 443 ssl http2;
    server_name api.UnSearch.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://UnSearch-api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

2. **Let's Encrypt with Certbot:**

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.UnSearch.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Monitoring & Observability

### Prometheus Metrics

Configure Prometheus to scrape metrics:

```yaml
scrape_configs:
  - job_name: "UnSearch-api"
    static_configs:
      - targets: ["api.UnSearch.com:8000"]
    metrics_path: "/metrics"
    scrape_interval: 15s
```

### Grafana Dashboard

Import the provided Grafana dashboard configuration for monitoring:

- Request rates and response times
- Error rates by endpoint
- Cache hit rates
- Service health status
- Resource utilization

### Log Aggregation

For centralized logging, configure your deployment to send logs to:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **AWS CloudWatch**
- **Google Cloud Logging**
- **Azure Monitor**

## 🔄 CI/CD Pipeline

### GitHub Actions Example

```yaml
name: Deploy UnSearch API

on:
  push:
    branches: [main]
  release:
    types: [published]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          make test-coverage

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: |
          docker build -t UnSearch/api:${{ github.sha }} .
          docker tag UnSearch/api:${{ github.sha }} UnSearch/api:latest
      - name: Deploy to production
        run: |
          # Your deployment commands here
          echo "Deploying to production..."
```

## 🔒 Security Checklist

- [ ] Use HTTPS everywhere
- [ ] Configure API keys
- [ ] Set up rate limiting
- [ ] Enable CORS protection
- [ ] Configure security headers
- [ ] Use strong database passwords
- [ ] Enable firewall rules
- [ ] Regular security updates
- [ ] Monitor for vulnerabilities
- [ ] Backup strategy in place

## 🚨 Troubleshooting

### Common Issues

1. **API not responding:**

   - Check service logs: `make logs`
   - Verify health endpoint: `curl http://localhost:8000/health`
   - Check database connectivity

2. **High response times:**

   - Monitor cache hit rates
   - Check SearXNG performance
   - Review concurrent request limits

3. **Memory issues:**

   - Monitor container resources
   - Check for memory leaks
   - Adjust worker counts

4. **Database connection errors:**
   - Verify connection string
   - Check database server status
   - Review connection pool settings

### Health Checks

Use the built-in monitoring script:

```bash
# Single health check
./scripts/monitor.sh

# Continuous monitoring
./scripts/monitor.sh http://api.UnSearch.com 30 monitor
```

## 📞 Support

For deployment issues:

1. Check the logs first
2. Review the health endpoints
3. Consult the troubleshooting section
4. Create an issue with detailed information

---

This deployment guide should cover most production scenarios. Adjust configurations based on your specific requirements and infrastructure.
