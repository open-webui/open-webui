#!/bin/bash

# Create the directory structure
mkdir -p ./certbot/conf/live/mergefeat.xyz

# Generate a self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./certbot/conf/live/mergefeat.xyz/privkey.pem \
  -out ./certbot/conf/live/mergefeat.xyz/fullchain.pem \
  -subj "/CN=mergefeat.xyz"

# Set proper permissions
sudo chmod -R 755 ./certbot/conf 