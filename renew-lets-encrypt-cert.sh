#!/bin/bash

# Log start of renewal process
echo "Starting Let's Encrypt certificate renewal process at $(date)" >> certbot-renewal.log

# Run certbot renewal
sudo docker run --rm \
  -v $PWD/certbot/conf:/etc/letsencrypt \
  -v $PWD/certbot/www:/var/www/certbot \
  certbot/certbot renew --webroot --webroot-path=/var/www/certbot >> certbot-renewal.log 2>&1

# Check result
if [ $? -eq 0 ]; then
  echo "Certificate renewal process completed successfully at $(date)" >> certbot-renewal.log
  
  # Restart nginx to pick up the renewed certificates
  sudo docker restart webui-nginx >> certbot-renewal.log 2>&1
else
  echo "Certificate renewal process failed at $(date)" >> certbot-renewal.log
fi 