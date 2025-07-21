# Hosting mAI and Models Separately

Sometimes, it's beneficial to host Ollama separate from the mAI UI, but retain the RAG and RBAC support features shared across users.

# mAI Apache Configuration

## UI Configuration

For the mAI UI configuration, you can set up the Apache VirtualHost as follows:

```apache
# Assuming you have a website hosting mAI at "server.com"
<VirtualHost 192.168.1.100:80>
    ServerName server.com
    DocumentRoot /home/server/public_html

    ProxyPass / http://server.com:8080/ nocanon
    ProxyPassReverse / http://server.com:8080/
    # WebSocket support (required for real-time features)
    ProxyPass /ws ws://server.com:8080/ws nocanon
    ProxyPassReverse /ws ws://server.com:8080/ws

</VirtualHost>
```

Enable the site first before you can request SSL:

`a2ensite server.com.conf` # this will enable the site. a2ensite is short for "Apache 2 Enable Site"

```apache
# For SSL
<VirtualHost 192.168.1.100:443>
    ServerName server.com
    DocumentRoot /home/server/public_html

    ProxyPass / http://server.com:8080/ nocanon
    ProxyPassReverse / http://server.com:8080/
    # WebSocket support (required for real-time features)
    ProxyPass /ws ws://server.com:8080/ws nocanon
    ProxyPassReverse /ws ws://server.com:8080/ws

    SSLEngine on
    SSLCertificateFile /etc/ssl/virtualmin/170514456861234/ssl.cert
    SSLCertificateKeyFile /etc/ssl/virtualmin/170514456861234/ssl.key
    SSLProtocol all -SSLv2 -SSLv3 -TLSv1 -TLSv1.1

    SSLProxyEngine on
    SSLCACertificateFile /etc/ssl/virtualmin/170514456865864/ssl.ca
</VirtualHost>
```

I'm using virtualmin here for my SSL clusters, but you can also use certbot directly or your preferred SSL method. To use SSL:

### Prerequisites

Run the following commands:

```bash
snap install certbot --classic
snap apt install python3-certbot-apache  # this will install the apache plugin
```

Navigate to the apache sites-available directory:

```bash
cd /etc/apache2/sites-available/
```

Create server.com.conf if it is not yet already created, containing the above `<virtualhost>` configuration (it should match your case. Modify as necessary). Use the one without the SSL.

Once it's created, run `certbot --apache -d server.com`, this will request and add/create SSL keys for you as well as create the server.com-le-ssl.conf

## Important Notes

### Port Configuration
- mAI runs on port **8080** by default (not 3000)
- Ensure your Docker container or mAI instance is configured to use the correct port
- WebSocket support is required for real-time chat features

### Headers for mAI
Add these headers for better compatibility:

```apache
<Location />
    Header set X-Forwarded-Proto "https"
    Header set X-Forwarded-For $proxy_add_x_forwarded_for
    Header set Host $http_host
</Location>
```

# Configuring Ollama Server

On your latest installation of Ollama, make sure that you have setup your API server from the official Ollama reference:

[Ollama FAQ](https://github.com/ollama/ollama/blob/main/docs/faq.md)

### TL;DR

The guide doesn't seem to match the current updated service file on Linux. So, we will address it here:

Unless when you're compiling Ollama from source, installing with the standard install `curl https://ollama.com/install.sh | sh` creates a file called `ollama.service` in /etc/systemd/system. You can use nano to edit the file:

```bash
sudo nano /etc/systemd/system/ollama.service
```

Add the following lines:

```ini
Environment="OLLAMA_HOST=0.0.0.0:11434" # this line is mandatory
```

For instance:

```ini
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
Environment="OLLAMA_HOST=0.0.0.0:11434" # this line is mandatory. You can also specify 192.168.254.109:DIFFERENT_PORT format
Environment="OLLAMA_ORIGINS=http://192.168.254.106:8080,https://models.server.city" # this line is optional
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin"

[Install]
WantedBy=default.target
```

Save the file by pressing CTRL+S, then press CTRL+X

Reload systemd and restart Ollama:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

When your computer restarts, the Ollama server will now be listening on the IP:PORT you specified, in this case 0.0.0.0:11434, or 192.168.254.106:11434 (whatever your local IP address is). Make sure that your router is correctly configured to serve pages from that local IP by forwarding 11434 to your local IP server.

# Ollama Model Configuration

## For the Ollama model configuration, use the following Apache VirtualHost setup:

Navigate to the apache sites-available directory:

```bash
cd /etc/apache2/sites-available/
nano models.server.city.conf  # match this with your ollama server domain
```

Add the following virtualhost containing this example (modify as needed):

```apache
# Assuming you have a website hosting Ollama at "models.server.city"
<IfModule mod_ssl.c>
    <VirtualHost 192.168.254.109:443>
        DocumentRoot "/var/www/html/"
        ServerName models.server.city
        <Directory "/var/www/html/">
            Options None
            Require all granted
        </Directory>

        ProxyRequests Off
        ProxyPreserveHost On
        ProxyAddHeaders On
        SSLProxyEngine on

        ProxyPass / http://localhost:11434/ nocanon
        ProxyPassReverse / http://localhost:11434/

        SSLCertificateFile /etc/letsencrypt/live/models.server.city/fullchain.pem
        SSLCertificateKeyFile /etc/letsencrypt/live/models.server.city/privkey.pem
        Include /etc/letsencrypt/options-ssl-apache.conf
    </VirtualHost>
</IfModule>
```

You may need to enable the site first (if you haven't done so yet) before you can request SSL:

```bash
a2ensite models.server.city.conf
```

#### For the SSL part of Ollama server

Run the following commands:

```bash
cd /etc/apache2/sites-available/
certbot --apache -d models.server.city
```

```apache
<VirtualHost 192.168.254.109:80>
    DocumentRoot "/var/www/html/"
    ServerName models.server.city
    <Directory "/var/www/html/">
        Options None
        Require all granted
    </Directory>

    ProxyRequests Off
    ProxyPreserveHost On
    ProxyAddHeaders On

    ProxyPass / http://localhost:11434/ nocanon
    ProxyPassReverse / http://localhost:11434/

    RewriteEngine on
    RewriteCond %{SERVER_NAME} =models.server.city
    RewriteRule ^ https://%{SERVER_NAME}%{REQUEST_URI} [END,NE,R=permanent]
</VirtualHost>
```

Don't forget to restart/reload Apache with `systemctl reload apache2`

Open your site at https://server.com!

## Complete Example Configuration

Here's a complete example with both mAI and Ollama on the same server:

```apache
# mAI UI
<VirtualHost *:443>
    ServerName ai.yourdomain.com
    
    # Proxy to mAI
    ProxyPass / http://localhost:8080/
    ProxyPassReverse / http://localhost:8080/
    
    # WebSocket support
    RewriteEngine on
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) "ws://localhost:8080/$1" [P,L]
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/ai.yourdomain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/ai.yourdomain.com/privkey.pem
</VirtualHost>

# Ollama API (if hosting separately)
<VirtualHost *:443>
    ServerName ollama.yourdomain.com
    
    ProxyPass / http://localhost:11434/
    ProxyPassReverse / http://localhost:11434/
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/ollama.yourdomain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/ollama.yourdomain.com/privkey.pem
</VirtualHost>
```

**Congratulations**, your **mAI (You + AI = superpowers! 🚀)** is now serving AI with RAG, RBAC and multimodal features! Download Ollama models if you haven't yet done so!

If you encounter any misconfiguration or errors, please file an issue or engage with our discussion. There are a lot of friendly developers here to assist you.

Let's make mAI much more user friendly for everyone!

Thanks for making mAI your UI Choice for AI!

This doc is based on the original by **Bob Reyes**, adapted for mAI.