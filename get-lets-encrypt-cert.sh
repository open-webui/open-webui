#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting Let's Encrypt certificate acquisition process..."

# Set domain
DOMAIN="hkust-search.mergefeat.xyz"
EMAIL="admin@mergefeat.xyz"

# Create the necessary directories
mkdir -p ./certbot/www/.well-known/acme-challenge
mkdir -p ./certbot/conf/live/$DOMAIN

# Set proper permissions for certbot directory
sudo chmod -R 755 ./certbot

# Clean up any problematic configurations
echo "Cleaning up any existing problematic configurations..."
sudo rm -f ./certbot/conf/renewal/$DOMAIN.conf
# Keep the existing certificates as backup if they exist
if [ -d "./certbot/conf/live/$DOMAIN" ]; then
  echo "Backing up existing certificates..."
  sudo mkdir -p ./certbot-backup/$(date +%Y%m%d)
  sudo cp -r ./certbot/conf/live/$DOMAIN ./certbot-backup/$(date +%Y%m%d)/
fi

echo "Obtaining new Let's Encrypt certificate..."
# Run certbot in standalone mode to obtain the certificate
sudo docker run -it --rm \
  -v $PWD/certbot/conf:/etc/letsencrypt \
  -v $PWD/certbot/www:/var/www/certbot \
  certbot/certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email $EMAIL \
  --agree-tos \
  --no-eff-email \
  --domain $DOMAIN \
  --force-renewal

# Make sure Docker has access to read the certificates
sudo chmod -R 755 ./certbot/conf

echo "Certificate acquisition process completed."
echo "Please check ./certbot/conf/live/$DOMAIN/ for your certificates."

# Verify that the certificates were properly created
if [ -f "./certbot/conf/live/$DOMAIN/fullchain.pem" ] && [ -f "./certbot/conf/live/$DOMAIN/privkey.pem" ]; then
  echo "Certificates were successfully generated!"
  
  # Check if the archive directory exists and contains the necessary files
  if [ -d "./certbot/conf/archive/$DOMAIN" ]; then
    echo "Archive directory exists and contains the certificate files."
  else
    echo "WARNING: Archive directory is missing. Certificates may not renew properly."
  fi
  
  # Check if the renewal configuration was created properly
  if [ -s "./certbot/conf/renewal/$DOMAIN.conf" ]; then
    echo "Renewal configuration was successfully created."
  else
    echo "WARNING: Renewal configuration is empty or missing. Certificates may not renew properly."
  fi
else
  echo "ERROR: Certificate generation failed. Please check the logs for more information."
  exit 1
fi 