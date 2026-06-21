---
rros_project: unsearch
rros_doc_id: unsearch/docs/ops/secrets-management.md
notion_page_id: 386e4a4b-2a11-8182-9994-e6b6acddbb3e
rros_domain: ops
---

# Secrets Management Guide
This guide provides comprehensive instructions for managing secrets, API keys, and sensitive configuration in the UnSearch API system.
## Table of Contents
1. [Overview](#overview)
2. [Secret Types](#secret-types)
3. [Local Development](#local-development)
4. [Production Deployment](#production-deployment)
5. [Secret Rotation](#secret-rotation)
6. [Security Best Practices](#security-best-practices)
7. [Troubleshooting](#troubleshooting)
## Overview
The UnSearch API uses multiple layers of secret management to ensure security:
- **Environment Variables**: For configuration and non-sensitive settings
- **Secret Stores**: For sensitive credentials (passwords, API keys, tokens)
- **Key Management Services**: For encryption keys and certificates
- **Audit Logging**: For tracking secret access and changes
## Secret Types
### 1. Application Secrets
<table header-row="true">
<tr>
<td>Secret</td>
<td>Description</td>
<td>Rotation Frequency</td>
<td>Impact</td>
</tr>
<tr>
<td>`SECRET_KEY`</td>
<td>JWT signing key</td>
<td>90 days</td>
<td>High - Invalidates all tokens</td>
</tr>
<tr>
<td>`API_KEYS`</td>
<td>Client API keys</td>
<td>On demand</td>
<td>Medium - Per client</td>
</tr>
<tr>
<td>`SEARXNG_SECRET_KEY`</td>
<td>SearXNG instance key</td>
<td>180 days</td>
<td>Low</td>
</tr>
</table>
### 2. Database Credentials
<table header-row="true">
<tr>
<td>Secret</td>
<td>Description</td>
<td>Rotation Frequency</td>
<td>Impact</td>
</tr>
<tr>
<td>`DATABASE_URL`</td>
<td>PostgreSQL connection</td>
<td>90 days</td>
<td>High - Requires downtime</td>
</tr>
<tr>
<td>`DB_PASSWORD`</td>
<td>Database password</td>
<td>90 days</td>
<td>High</td>
</tr>
<tr>
<td>`DB_ENCRYPTION_KEY`</td>
<td>Data encryption key</td>
<td>Never\*</td>
<td>Critical</td>
</tr>
</table>
\*Encryption keys should be versioned, not rotated
### 3. External Service Keys
<table header-row="true">
<tr>
<td>Secret</td>
<td>Description</td>
<td>Rotation Frequency</td>
<td>Impact</td>
</tr>
<tr>
<td>`AWS_ACCESS_KEY_ID`</td>
<td>AWS credentials</td>
<td>60 days</td>
<td>Medium</td>
</tr>
<tr>
<td>`AWS_SECRET_ACCESS_KEY`</td>
<td>AWS secret</td>
<td>60 days</td>
<td>Medium</td>
</tr>
<tr>
<td>`SENTRY_DSN`</td>
<td>Error tracking</td>
<td>On demand</td>
<td>Low</td>
</tr>
<tr>
<td>`SLACK_WEBHOOK_URL`</td>
<td>Notifications</td>
<td>On demand</td>
<td>Low</td>
</tr>
</table>
### 4. Infrastructure Secrets
<table header-row="true">
<tr>
<td>Secret</td>
<td>Description</td>
<td>Rotation Frequency</td>
<td>Impact</td>
</tr>
<tr>
<td>`REDIS_PASSWORD`</td>
<td>Cache auth</td>
<td>90 days</td>
<td>Medium</td>
</tr>
<tr>
<td>`CELERY_BROKER_URL`</td>
<td>Queue auth</td>
<td>90 days</td>
<td>Medium</td>
</tr>
<tr>
<td>`PROMETHEUS_BEARER_TOKEN`</td>
<td>Metrics auth</td>
<td>180 days</td>
<td>Low</td>
</tr>
</table>
## Local Development
### Using .env Files
1. **Create .env from template**:
```bash
cp .env.example .env
```
1. **Generate secure secrets**:
```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate API key
python -c "import secrets; print(f'sk_{secrets.token_urlsafe(32)}')"

# Generate strong password
openssl rand -base64 32
```
1. **Set permissions**:
```bash
chmod 600 .env
```
### Using direnv (Recommended)
1. **Install direnv**:
```bash
# macOS
brew install direnv

# Linux
apt-get install direnv
```
1. **Create .envrc**:
```bash
cat > .envrc << 'EOF'
# Load environment variables
dotenv .env

# Add project scripts to PATH
PATH_add scripts

# Activate Python virtual environment
source venv/bin/activate
EOF
```
1. **Allow direnv**:
```bash
direnv allow
```
## Production Deployment
### Using AWS Secrets Manager
1. **Store secrets in AWS**:
```bash
# Create secret
aws secretsmanager create-secret \
    --name UnSearch/production/api \
    --secret-string file://secrets.json

# Update secret
aws secretsmanager update-secret \
    --secret-id UnSearch/production/api \
    --secret-string file://secrets.json
```
1. **Retrieve secrets in application**:
```python
import boto3
import json

def get_secrets():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='UnSearch/production/api')
    return json.loads(response['SecretString'])
```
1. **IAM policy for access**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:UnSearch/*"
    }
  ]
}
```
### Using HashiCorp Vault
1. **Install Vault**:
```bash
# Docker
docker run -d --cap-add=IPC_LOCK \
    -e 'VAULT_LOCAL_CONFIG={"storage": {"file": {"path": "/vault/file"}}, "listener": {"tcp": {"address": "0.0.0.0:8200", "tls_disable": true}}}' \
    -p 8200:8200 vault:latest
```
1. **Store secrets**:
```bash
# Enable KV secrets engine
vault secrets enable -path=UnSearch kv-v2

# Write secrets
vault kv put UnSearch/production \
    database_url="postgresql://..." \
    redis_url="redis://..." \
    secret_key="..."
```
1. **Retrieve secrets**:
```python
import hvac

client = hvac.Client(url='http://vault:8200', token='...')
secrets = client.secrets.kv.v2.read_secret_version(
    path='production',
    mount_point='UnSearch'
)['data']['data']
```
### Using Kubernetes Secrets
1. **Create secret**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: UnSearch-secrets
  namespace: production
type: Opaque
data:
  database-url: <base64-encoded-value>
  redis-url: <base64-encoded-value>
  secret-key: <base64-encoded-value>
```
1. **Apply secret**:
```bash
kubectl apply -f secrets.yaml
```
1. **Use in deployment**:
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: api
          envFrom:
            - secretRef:
                name: UnSearch-secrets
```
### Using Docker Secrets
1. **Create secrets**:
```bash
# Create secret files
echo "postgresql://..." | docker secret create db_url -
echo "redis://..." | docker secret create redis_url -
```
1. **Use in docker-compose**:
```yaml
version: "3.8"
services:
  api:
    secrets:
      - db_url
      - redis_url
    environment:
      DATABASE_URL_FILE: /run/secrets/db_url
      REDIS_URL_FILE: /run/secrets/redis_url

secrets:
  db_url:
    external: true
  redis_url:
    external: true
```
## Secret Rotation
### Automated Rotation Script
```bash
#!/bin/bash
# scripts/rotate-secrets.sh

# Rotate database password
NEW_DB_PASS=$(openssl rand -base64 32)
psql -c "ALTER USER UnSearch WITH PASSWORD '$NEW_DB_PASS';"

# Update secret store
aws secretsmanager update-secret \
    --secret-id UnSearch/production/db \
    --secret-string "{\"password\": \"$NEW_DB_PASS\"}"

# Restart services
docker-compose restart api celery-worker
```
### Manual Rotation Procedure
1. **Generate new secret**
2. **Update secret in staging**
3. **Test in staging**
4. **Schedule maintenance window**
5. **Update production secret**
6. **Deploy with new secret**
7. **Verify functionality**
8. **Revoke old secret**
### API Key Rotation
```python
# Generate new API key
import secrets
import hashlib

def generate_api_key():
    key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    # Store hash in database
    save_api_key_hash(key_hash)

    # Return key to user (only shown once)
    return f"sk_{key}"

def rotate_api_key(old_key_id):
    # Generate new key
    new_key = generate_api_key()

    # Set expiration for old key
    set_key_expiration(old_key_id, days=7)

    # Notify user
    send_rotation_notification(new_key)

    return new_key
```
## Security Best Practices
### 1. Never Commit Secrets
**.gitignore**:
```plain text
# Environment files
.env
.env.*
!.env.example

# Secret files
*.pem
*.key
*.crt
secrets/
credentials/

# Terraform state
*.tfstate
*.tfstate.*
```
### 2. Use Secret Scanning
**Pre-commit hook** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]
```
### 3. Encrypt Secrets at Rest
```python
from cryptography.fernet import Fernet

def encrypt_secret(secret: str, key: bytes) -> str:
    f = Fernet(key)
    encrypted = f.encrypt(secret.encode())
    return encrypted.decode()

def decrypt_secret(encrypted: str, key: bytes) -> str:
    f = Fernet(key)
    decrypted = f.decrypt(encrypted.encode())
    return decrypted.decode()
```
### 4. Audit Secret Access
```python
import logging
from datetime import datetime

audit_logger = logging.getLogger('audit')

def log_secret_access(user_id: str, secret_name: str, action: str):
    audit_logger.info({
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'secret_name': secret_name,
        'action': action,
        'ip_address': get_client_ip(),
        'user_agent': get_user_agent()
    })
```
### 5. Principle of Least Privilege
```yaml
# IAM Policy Example
{
  "Version": "2012-10-17",
  "Statement":
    [
      {
        "Sid": "ReadOnlyProductionSecrets",
        "Effect": "Allow",
        "Principal":
          { "AWS": "arn:aws:iam::123456789012:role/UnSearch-api" },
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": "arn:aws:secretsmanager:*:*:secret:UnSearch/production/*",
        "Condition": { "IpAddress": { "aws:SourceIp": ["10.0.0.0/8"] } },
      },
    ],
}
```
## Environment-Specific Configuration
### Development
```bash
# .env.development
DEBUG=true
SECRET_KEY=development-only-secret
DATABASE_URL=postgresql://dev:dev@localhost:5432/UnSearch_dev
```
### Staging
```bash
# Use AWS Secrets Manager
export SECRET_ARN=arn:aws:secretsmanager:us-east-1:123456789012:secret:UnSearch/staging
```
### Production
```bash
# Use Vault
export VAULT_ADDR=https://vault.example.com:8200
export VAULT_TOKEN=$(vault login -method=aws -token-only)
```
## Troubleshooting
### Common Issues
1. **Secret not found**:
```bash
# Check environment
env | grep -i secret

# Check secret store
aws secretsmanager get-secret-value --secret-id UnSearch/production

# Check permissions
aws sts get-caller-identity
```
1. **Permission denied**:
```bash
# Verify IAM role
aws sts assume-role --role-arn arn:aws:iam::123456789012:role/UnSearch-api

# Check policy
aws iam get-role-policy --role-name UnSearch-api --policy-name secrets-access
```
1. **Secret rotation failed**:
```bash
# Check rotation status
aws secretsmanager describe-secret --secret-id UnSearch/production

# View rotation history
aws secretsmanager list-secret-version-ids --secret-id UnSearch/production

# Manually trigger rotation
aws secretsmanager rotate-secret --secret-id UnSearch/production
```
### Emergency Procedures
1. **Compromised Secret**:
```bash
# 1. Immediately rotate the secret
./scripts/emergency-rotation.sh <secret-name>

# 2. Audit access logs
./scripts/audit-secret-access.sh <secret-name> --days 30

# 3. Update all services
kubectl rollout restart deployment/UnSearch-api

# 4. Notify security team
./scripts/security-notification.sh --severity critical
```
1. **Lost Access to Secrets**:
```bash
# 1. Use break-glass credentials
export BREAK_GLASS_TOKEN=$(cat /secure/break-glass-token)

# 2. Restore access
vault operator unseal

# 3. Re-encrypt secrets
./scripts/re-encrypt-all-secrets.sh
```
## Compliance and Regulations
### GDPR Compliance
- Encrypt PII at rest and in transit
- Implement key versioning for data portability
- Maintain audit logs for 2 years
### SOC 2 Requirements
- Rotate secrets every 90 days
- Use MFA for secret access
- Implement secret scanning in CI/CD
### PCI DSS
- Never store unencrypted card data
- Use HSM for payment-related keys
- Implement split knowledge for critical secrets
## Tools and References
### Secret Management Tools
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [HashiCorp Vault](https://www.vaultproject.io/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
- [Azure Key Vault](https://azure.microsoft.com/en-us/services/key-vault/)
- [Google Secret Manager](https://cloud.google.com/secret-manager)
### Security Scanners
- [detect-secrets](https://github.com/Yelp/detect-secrets)
- [git-secrets](https://github.com/awslabs/git-secrets)
- [truffleHog](https://github.com/trufflesecurity/trufflehog)
- [GitLeaks](https://github.com/zricethezav/gitleaks)
### Encryption Libraries
- [cryptography](https://cryptography.io/)
- [pynacl](https://pynacl.readthedocs.io/)
- [passlib](https://passlib.readthedocs.io/)
## Contact Information
For security concerns or questions:
- Security contact: [security@unsearch.dev](mailto:security@unsearch.dev)
- On-call: *your paging tool*
- Chat: *your security channel*
