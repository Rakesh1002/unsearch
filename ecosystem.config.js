/**
 * UnSearch PM2 Ecosystem Configuration
 * 
 * Manages:
 * - Backend: FastAPI with uvicorn (4 workers)
 * - Frontend: Next.js production server
 * - Docker services are managed separately via docker compose
 */

module.exports = {
  apps: [
    {
      name: 'unsearch-backend',
      cwd: './',
      script: './venv/bin/uvicorn',
      args: 'app.main:app --host 127.0.0.1 --port 8000 --workers 4',
      interpreter: 'none',
      env: {
        PATH: './venv/bin:/usr/local/bin:/usr/bin:/bin',
        PYTHONPATH: './',
        // Load environment from .env file
        NODE_ENV: 'production',
      },
      env_file: './.env',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      log_file: './logs/backend-combined.log',
      time: true,
      merge_logs: true,
      // Graceful shutdown
      kill_timeout: 10000,
      wait_ready: true,
      listen_timeout: 30000,
    },
    {
      name: 'unsearch-frontend',
      cwd: './apps/web',
      script: 'pnpm',
      args: 'start',
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        PORT: '3000',
      },
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      error_file: './logs/frontend-error.log',
      out_file: './logs/frontend-out.log',
      log_file: './logs/frontend-combined.log',
      time: true,
      merge_logs: true,
      // Graceful shutdown
      kill_timeout: 5000,
    },
  ],

  // Deployment configuration (optional)
  deploy: {
    production: {
      user: 'root',
      host: 'your-server-ip',
      ref: 'origin/main',
      repo: 'git@github.com:Rakesh1002/unsearch.git',
      path: '/opt/unsearch',
      'pre-deploy-local': '',
      'post-deploy': 'npm install && pm2 reload ecosystem.config.js --env production',
      'pre-setup': '',
    },
  },
};
