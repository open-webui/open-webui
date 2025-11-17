# Deployment Guide for AWS Lightsail

This guide explains how to use the `deploy.sh` script to deploy the Bio-Rad Customer Service Cockpit to AWS Lightsail.

### DEV
```bash
prod:
ssh -i Customer-Inquiry.pem ubuntu@52.41.164.103

dev:
ssh -i customer-inquiry-dev.pem ubuntu@54.214.101.235
```

### QA
```bash
ssh -i customer-inquiry-qa.pem ubuntu@44.253.33.174
```

### RUN ON SERVER TO UPDATE:

```bash
cd bio-rad-customer-service-cockpit
git pull origin master
pm2 stop 0
npm run build
pm2 start 0
```

### INITIAL SETUP ON SERVER:
```bash
vi ~/.ssh/config 
```

```text
Host github-customer-inquiry
    HostName github.com
    User git
    IdentityFile ~/.ssh/customer-inquiry
    IdentitiesOnly yes
```

Add the customer-inquiry and customer-inquiry.pub keys for github.

```bash
chmod 600 ~/.ssh/customer-inquiry
chmod 644 .ssh/customer-inquiry.pub
```

Copy deploy-server.sh to server:
```bash
scp -r deploy-server.sh ubuntu@44.253.33.174:~
```

```bash
chmod +x deploy-server.sh
./deploy-server.sh git@github-customer-inquiry:diverse-programmers/bio-rad-customer-service-cockpit gitcomplaints 44.253.33.174 3000
exit
```

exit and reconnect to make sure everything is set. run:
```bash
node -v
```

REMEMBER TO ADD THE .env
NOTE: MAKE SURE YOU SET THE CORRECT "REDIRECT_URI"
```
cd bio-rad-customer-service-cockpit
vi .env
npm run build
pm2 start 0
```

Log into Azure:
Privileged Identity Management - Grant permission
https://portal.azure.com/?feature.msaljs=true#view/Microsoft_Azure_PIMCommon/CommonMenuBlade/~/quickStart

App registrations - All Applications
https://portal.azure.com/?feature.msaljs=true#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade

Find app - customer-inquiry-ai
https://portal.azure.com/?feature.msaljs=true#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/fd646d27-085f-49ec-85ef-132abcb2f627/isMSAApp~/false

Add to Web Redirect URIs
cloudfront IP, ex: https://d25l6wampynkno.cloudfront.net/api/auth/callback
web endpoint, ex: https://customer-service.app.bio-rad.com/api/auth/callback

letsencrypt:
sudo apt update 
sudo apt install -y nginx
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo ufw allow 'Nginx Full' || true
sudo certbot --nginx   -d origin.dev.customer-service.app.bio-rad.com   --redirect --agree-tos -m james_malin@bio-rad.com -n

```bash
sudo rm /etc/nginx/sites-available/nextjs
sudo vi /etc/nginx/sites-available/nextjs
```

```bash
sudo ln -sf /etc/nginx/sites-available/nextjs /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Prerequisites

1. AWS Lightsail instance running Ubuntu
2. SSH access to your Lightsail instance
3. Node.js installed on your local machine
4. Access to the project repository

## Deployment Steps

### 1. Local Preparation

Run the deployment script locally:
```bash
./deploy.sh
```

This script will:
- Build the application
- Create a `deploy` directory
- Copy necessary production files
- Generate a production start script

### 2. Upload to Lightsail

Replace `YOUR_LIGHTSAIL_IP` with your actual Lightsail instance IP:
```bash
scp -r ./deploy/* ubuntu@YOUR_LIGHTSAIL_IP:/home/ubuntu/bio-rad-customer-service-cockpit/
```

### 3. Server Setup

1. SSH into your Lightsail instance:
```bash
ssh ubuntu@YOUR_LIGHTSAIL_IP
```

2. Navigate to the application directory:
```bash
cd /home/ubuntu/bio-rad-customer-service-cockpit
```

3. Run the start script:
```bash
./start.sh
```

The application will:
- Install production dependencies
- Start the server on port 8080
- Run in production mode

## Verification

After deployment:
1. The application should be running on port 8080
2. Access your application at: `http://YOUR_LIGHTSAIL_IP:8080`
3. Check the logs in the terminal for any errors

## Troubleshooting

1. If the server fails to start, check:
   - Node.js is installed on the Lightsail instance
   - Port 8080 is open in your Lightsail firewall settings
   - All files were copied correctly

2. If you see permission errors:
   ```bash
   chmod +x start.sh
   ```

3. To view logs:
   ```bash
   pm2 logs # if using PM2
   # or
   tail -f /path/to/your/log/file
   ```

4. If redirect is incorrect on server from microsoft auth back to app (loop):
check nginx

then run:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Notes

- The application runs in production mode
- Server-side rendering is enabled
- Static assets are served from the `dist` directory
- Environment variables should be set on the Lightsail instance if required
