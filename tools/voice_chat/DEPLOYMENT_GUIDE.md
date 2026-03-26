# 🚀 RAJ DEPLOYMENT GUIDE - Multi-Server Production Setup

**Last Updated**: March 25, 2026  
**Status**: Ready for Production  
**Architecture**: 2x Backend Servers + Load Balancer + Redis + PostgreSQL

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Local)](#quick-start-local)
3. [Production Deployment (Cloud)](#production-deployment-cloud)
4. [Multi-Server Failover](#multi-server-failover)
5. [Monitoring & Logs](#monitoring--logs)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

---

## Prerequisites

### Required
- **Docker & Docker Compose** (v20.10+)
- **Linux Server** (Ubuntu 20.04+ recommended) OR Mac for local dev
- **API Keys**:
  - Anthropic (Claude API)
  - Twilio (WhatsApp/SMS)
  - Instagram Business API
- **Public Domain** (optional, for SSL)

### Optional but Recommended
- **AWS Account** or similar cloud provider
- **SSL Certificate** (Let's Encrypt free)
- **Monitoring Tool** (DataDog, New Relic, etc.)

---

## Quick Start (Local)

Perfect for testing before deployment.

### Step 1: Prepare Environment

```bash
cd ~/Documents/AI\ Projects/Personal\ Assistant/tools/voice_chat

# Create .env file with your credentials
cat > .env << 'EOF'
# PostgreSQL
DB_USER=mo
DB_PASSWORD=your_super_secure_password_here
DB_NAME=raj_db
DB_PORT=5432

# Redis
REDIS_PORT=6379

# API Keys
ANTHROPIC_API_KEY=sk-ant-your-key-here
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-twilio-token-here
TWILIO_PHONE=+1234567890

# Instagram
INSTAGRAM_ACCESS_TOKEN=your-instagram-token-here
INSTAGRAM_BUSINESS_ACCOUNT_ID=your-business-account-id

# Mo's Phone Numbers
MO_WHATSAPP_PHONE=+1234567890
MO_PHONE=+1234567890
EOF
```

### Step 2: Start All Services

```bash
# Build and start all containers
docker-compose up -d

# Wait for services to initialize (30-60 seconds)
sleep 30

# Check if all services are healthy
docker-compose ps

# Should show:
# NAME                 STATUS              PORTS
# raj_postgres         Up (healthy)        0.0.0.0:5432->5432/tcp
# raj_redis           Up (healthy)        0.0.0.0:6379->6379/tcp
# raj_backend_1       Up (healthy)        0.0.0.0:8001->8001/tcp
# raj_backend_2       Up (healthy)        0.0.0.0:8002->8002/tcp
# raj_scheduler       Up                   (no external ports)
# raj_nginx           Up (healthy)        0.0.0.0:80->80/tcp
```

### Step 3: Verify It's Working

```bash
# Health check (should return 200 OK)
curl http://localhost/health

# Expected response:
# {"status":"online","timestamp":"2026-03-25T10:30:45","version":"1.0.0"}

# Check pending first contacts (should be empty)
curl http://localhost/first-contact/pending

# Get dashboard summary
curl http://localhost/dashboard/summary
```

### Step 4: Test Message Flow

```bash
# Send a test message via API
curl -X POST http://localhost/message/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "whatsapp",
    "from": "+1234567890",
    "message": "Hey, interested in custom piece",
    "customer_name": "Ahmed"
  }'

# Response should include:
# - "status": "success" OR "awaiting_approval" (if first contact)
# - "queued_message_id": (the message in queue)
# - "delay_info": "Queued with 120s delay" (example)

# After 1-5 minutes, message should be sent via Twilio
```

### Step 5: Stop Services

```bash
# Stop all containers (keeps data)
docker-compose down

# Stop and remove all data (clean slate)
docker-compose down -v
```

---

## Production Deployment (Cloud)

Deploy on AWS, DigitalOcean, Azure, or your preferred cloud.

### Option A: AWS EC2 + RDS (Recommended)

#### Set Up EC2 Instance

```bash
# 1. Launch Ubuntu 20.04 LTS instance (t3.medium minimum)
# 2. Security Group: Allow inbound on 80, 443, SSH (22)
# 3. SSH into instance

ssh -i your-key.pem ubuntu@your-ec2-public-ip

# 4. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu

# 5. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 6. Clone your Raj repository
git clone https://github.com/yourusername/raj.git
cd raj/tools/voice_chat
```

#### Set Up RDS PostgreSQL

```bash
# Via AWS Console:
# 1. RDS → Create Database
# 2. PostgreSQL 15
# 3. db.t3.micro (free tier) or db.t3.small (production)
# 4. Storage: 20 GB, Enable backups (7 days)
# 5. Public Accessibility: No (keep internal)
# 6. Subnet: Same as EC2
# 7. Security Group: Allow EC2 instance access on port 5432
```

#### Configure Environment

```bash
# Create .env for production
cat > .env << 'EOF'
# RDS PostgreSQL
DATABASE_URL=postgresql://mo:your_secure_password@your-rds-endpoint.amazonaws.com:5432/raj_db
DB_USER=mo
DB_PASSWORD=your_secure_password
DB_NAME=raj_db

# Redis (local container)
REDIS_URL=redis://localhost:6379/0
REDIS_PORT=6379

# API Keys (use AWS Secrets Manager in production)
ANTHROPIC_API_KEY=sk-ant-your-key
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-token
TWILIO_PHONE=+1234567890
INSTAGRAM_ACCESS_TOKEN=your-token
INSTAGRAM_BUSINESS_ACCOUNT_ID=your-id
MO_WHATSAPP_PHONE=+1234567890
MO_PHONE=+1234567890

# SSL/TLS (for HTTPS)
SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
EOF
```

#### Set Up SSL (Let's Encrypt)

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate (point DNS to EC2 IP first)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Update nginx.conf to use SSL
# Uncomment HTTPS section and configure paths
```

#### Launch Production Services

```bash
# Start all services in background
docker-compose -f docker-compose.yml up -d

# Check logs
docker-compose logs -f raj_nginx

# Monitor system resources
watch -n 2 'docker stats --no-stream'
```

### Option B: DigitalOcean App Platform (Simplest)

```bash
# 1. Create DigitalOcean account
# 2. Go to App Platform
# 3. Connect GitHub repository
# 4. Create app.yaml:

name: raj
services:
  - name: raj-backend-1
    image_path: backend
    http_port: 8001
  - name: raj-backend-2
    image_path: backend
    http_port: 8002
  - name: raj-scheduler
    image_path: backend
    build_command: python jobs.py
databases:
  - name: postgres
    version: 15
  - name: redis
    version: 7

# 5. Add environment variables to App Platform console
# 6. Deploy
```

### Option C: Docker Swarm (If Scaling Across Multiple Machines)

```bash
# Initialize Swarm on primary node
docker swarm init

# Join secondary nodes
docker swarm join --token SWMTKN-... your-primary-ip:2377

# Deploy stack
docker stack deploy -c docker-compose.yml raj

# Scale services
docker service scale raj_raj_backend=4  # 4 instances
```

---

## Multi-Server Failover

### How It Works

1. **Nginx Load Balancer** routes traffic to raj_server_1 and raj_server_2
2. **Redis** maintains shared state (message queue, customer overrides)
3. **PostgreSQL** is the single source of truth
4. If one server dies, Nginx automatically routes to the other
5. **Scheduler** runs on one instance, uses Redis lock to prevent duplication

### Test Failover

```bash
# Simulate Server 1 crashing
docker-compose kill raj_server_1

# Send a message - should still work (goes to Server 2)
curl -X POST http://localhost/message/incoming \
  -H "Content-Type: application/json" \
  -d '{"channel":"whatsapp","from":"+1234567890","message":"Test"}'

# Bring Server 1 back online
docker-compose up -d raj_server_1

# Both servers now handling traffic again
docker-compose ps
```

### Health Checks

Nginx automatically removes unhealthy backends:

```bash
# In nginx.conf:
# max_fails=3 fail_timeout=30s  
# = Remove backend after 3 failed health checks within 30 seconds
```

---

## Monitoring & Logs

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f raj_server_1
docker-compose logs -f raj_nginx
docker-compose logs -f raj_scheduler

# Search for errors
docker-compose logs | grep "ERROR"

# Last 100 lines
docker-compose logs --tail 100
```

### Performance Metrics

```bash
# Monitor container resources
docker stats

# Database queries (PostgreSQL)
docker exec -it raj_postgres psql -U mo -d raj_db -c "SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Redis memory usage
docker exec -it raj_redis redis-cli INFO memory

# Message queue depth (how many messages waiting to send)
docker exec -it raj_postgres psql -U mo -d raj_db -c "SELECT COUNT(*) FROM message_queue WHERE status='queued';"
```

### Set Up Alerts

**Email Alert on Server Down** (using Docker events):

```bash
# Create alert script
cat > alert.sh << 'EOF'
#!/bin/bash
while true; do
  docker-compose ps | grep -i "exited" && {
    echo "⚠️ Service down!" | mail -s "Raj Alert" your@email.com
    sleep 300  # Wait 5 min before checking again
  }
  sleep 30
done
EOF

chmod +x alert.sh
nohup ./alert.sh &
```

---

## Troubleshooting

### Issue: "Connection refused" to PostgreSQL

```bash
# Check if postgres container is running
docker-compose ps | grep postgres

# If not running, check logs
docker-compose logs postgres

# Rebuild postgres
docker-compose down -v postgres
docker-compose up -d postgres
```

### Issue: Messages Not Sending

```bash
# Check message queue
docker exec -it raj_postgres psql -U mo -d raj_db -c "SELECT * FROM message_queue WHERE status='failed' LIMIT 5;"

# Check scheduler logs
docker-compose logs raj_scheduler | tail -50

# Verify Twilio credentials
docker exec -it raj_server_1 python -c "from integrations.twilio_handler import TwilioMessenger; TwilioMessenger().send_whatsapp('+1234567890', 'Test')"
```

### Issue: High CPU/Memory Usage

```bash
# Check which container is consuming resources
docker stats

# If backend is consuming too much:
# 1. Increase container limits in docker-compose.yml
# 2. Add memory limit: "mem_limit: 1g"
# 3. Restart: docker-compose up -d

# If database is consuming too much:
# 1. Run VACUUM ANALYZE to optimize
docker exec -it raj_postgres psql -U mo -d raj_db -c "VACUUM ANALYZE;"

# 2. Check for long-running queries
docker exec -it raj_postgres psql -U mo -d raj_db -c "SELECT * FROM pg_stat_activity WHERE state != 'idle';"
```

### Issue: Nginx showing 502 Bad Gateway

```bash
# Current backend is unhealthy
docker-compose ps

# Check backend logs
docker-compose logs raj_server_1 | tail -50

# Restart backend
docker-compose restart raj_server_1

# Verify health endpoint
curl localhost:8001/health
```

### Issue: Redis Connection Error

```bash
# Restart Redis
docker-compose restart raj_redis

# Verify Redis is accessible
docker exec -it raj_redis redis-cli ping
# Should return: PONG

# Check Redis logs
docker-compose logs redis
```

---

## Maintenance

### Database Backups

```bash
# Manual backup
docker exec raj_postgres pg_dump -U mo raj_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker exec -i raj_postgres psql -U mo raj_db < backup_20260325_120000.sql

# Automated daily backup (add to crontab)
0 2 * * * docker exec raj_postgres pg_dump -U mo raj_db > /backups/raj_$(date +\%Y\%m\%d).sql
```

### Update Dependencies

```bash
# Update all containers to latest images
docker-compose pull
docker-compose up -d

# Or update specific service
docker-compose pull raj_server_1
docker-compose up -d raj_server_1
```

### Clean Up Old Data

```bash
# Remove old queued messages (older than 7 days)
docker exec -it raj_postgres psql -U mo -d raj_db -c "DELETE FROM message_queue WHERE created_at < NOW() - INTERVAL '7 days';"

# Remove old conversations (older than 1 year)
docker exec -it raj_postgres psql -U mo -d raj_db -c "DELETE FROM conversations WHERE created_at < NOW() - INTERVAL '1 year';"

# Optimize database
docker exec -it raj_postgres psql -U mo -d raj_db -c "VACUUM ANALYZE;"
```

### Upgrade PostgreSQL Version

```bash
# Backup first!
docker exec raj_postgres pg_dump -U mo raj_db > backup_before_upgrade.sql

# Change version in docker-compose.yml: postgres:15-alpine → postgres:16-alpine

# Recreate container
docker-compose down postgres
docker-compose up -d postgres

# Verify
docker exec -it raj_postgres psql --version
```

---

## Performance Tuning

### PostgreSQL Optimization

```bash
# Adjust postgresql.conf for your server specs
# For 4GB RAM server:

shared_buffers = 1GB
effective_cache_size = 3GB
maintenance_work_mem = 256MB
random_page_cost = 1.1
```

### Redis Optimization

```bash
# Increase max memory
docker exec -it raj_redis redis-cli CONFIG SET maxmemory 2gb
docker exec -it raj_redis redis-cli CONFIG REWRITE  # Save config
```

### Nginx Optimization

```bash
# Increase worker connections in nginx.conf
worker_connections 2048;

# Enable keepalive to backend
upstream raj_backend {
  keepalive 64;
}
```

---

## Scaling Checklist

Ready to scale? Use this checklist:

- [ ] Database has automated backups
- [ ] SSL/TLS certificate installed
- [ ] Monitoring in place (logs, alerts)
- [ ] Load testing completed (simulate 1000s concurrent users)
- [ ] Disaster recovery plan documented
- [ ] Team trained on runbooks (troubleshooting)
- [ ] Rate limiting tuned for your traffic
- [ ] Database indexes optimized
- [ ] Redis memory limits set
- [ ] Auto-scaling policies configured

---

## Support & Questions

**Raj is running in production!** 

Monitor these logs daily:
```bash
docker-compose logs -f | grep -E "ERROR|WARNING"
```

Keep these handy:
- Database credentials (in `.env`)
- API key backups (store in secure vault)
- SSL certificate renewal dates (certbot auto-renews)
- Contact info for Twilio/Anthropic support

---

**Status**: ✅ Raj is production-ready and fault-tolerant

**Next Steps:**
1. Choose your deployment platform (AWS/DigitalOcean/other)
2. Set up SSL certificate
3. Configure backups
4. Deploy to production
5. Test failover
6. Monitor logs
7. Celebrate! 🎉

---

**Questions?**
- Check logs: `docker-compose logs -f`
- Restart service: `docker-compose restart [service]`
- Check health: `curl http://localhost/health`
- See all commands: `docker-compose help`
