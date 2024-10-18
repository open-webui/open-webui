# Rishika WebUI Backend Setup

This document outlines the steps to set up and run the backend of Rishika WebUI.

---

## Prerequisites

Ensure you have the following installed:
- Node.js and npm
- Python and virtual environment tools

---

## Step-by-Step Backend Setup Instructions

1. **Navigate to the `open-webui` directory**:

    ```bash
    cd open-webui
    ```

2. **Change directory to the backend**:

    ```bash
    cd backend
    ```

3. **Build the backend using npm**:

    To build the necessary backend files, run:

    ```bash
    npm run build
    ```

4. **Activate the Python virtual environment**:

    Ensure you have set up your Python virtual environment. To activate it:

    ```bash
    source rishika/bin/activate
    ```

5. **Run the backend in the background**:

    Use `nohup` to run the backend process in the background. This will log the output into `openwebui.log`:

    ```bash
    nohup ./start.sh > openwebui.log 2>&1 &
    ```

6. **Monitor the logs**:

    To monitor the backend logs in real-time, use the `tail` command:

    ```bash
    tail -f openwebui.log
    ```

---

## Additional Notes

- Ensure the `start.sh` script has the appropriate executable permissions. If not, you can give the file executable rights using:

    ```bash
    chmod +x start.sh
    ```

- In case you encounter issues during the process, refer to the logs (`openwebui.log`) for error details or troubleshoot further.



# SSL Certificate Installation Guide

This document provides step-by-step instructions for installing SSL certificates using Certbot on your server.

---

## Steps to Install SSL Certificate

### 1. Create the `install_ssl.sh` Script

First, create a new shell script using `vi` or your preferred text editor:

```bash
vi install_ssl.sh
```

### 2. Add the Following Script

Copy and paste the following Bash script into `install_ssl.sh`. This script installs Certbot, prompts for the domain and email, and sets up the SSL certificate:

```bash
#!/bin/bash
sudo apt-get update
sudo apt-get install -y certbot

function install_ssl() {
    read -p "Enter the domain name (e.g., example.com): " DOMAIN
    read -p "Enter your email address: " EMAIL
    echo "Obtaining SSL certificate for $DOMAIN..."
    
    if sudo certbot certonly --standalone -d $DOMAIN --email $EMAIL --agree-tos --no-eff-email; then
        CERT_PATH=$(sudo certbot certificates | grep -oP '(?<=Certificate Path: ).*')
        KEY_PATH=$(sudo certbot certificates | grep -oP '(?<=Private Key Path: ).*')
        
        # Create directory for certificates
        sudo mkdir -p ./cert
        sudo cp $CERT_PATH ./cert/cert.pem
        sudo cp $KEY_PATH ./cert/key.pem
        
        # Set permissions (consider using more secure permissions)
        sudo chmod 644 $CERT_PATH
        sudo chmod 600 $KEY_PATH
        
        echo "SSL certificate has been installed."
        echo "Certificate Path: $CERT_PATH"
        echo "Private Key Path: $KEY_PATH"
    else
        echo "Failed to obtain SSL certificate."
    fi
}

install_ssl
```

### 3. Save and Exit

After entering the script, save the file and exit the editor by typing:

```
:wq
```

### 4. Run the Script

Now that the script is ready, run it to install the SSL certificate:

```bash
./install_ssl.sh
```

### 5. Check the Installed SSL Certificates

After successful installation, you can check the details of the installed SSL certificates using the following command:

```bash
sudo certbot certificates
```

---

## Additional Information

- The SSL certificates will be stored in the `./cert` directory, with `cert.pem` being the certificate and `key.pem` being the private key.
- The script sets permissions for the certificate files, but it is advisable to review these and ensure they comply with your security policies.
  
If the script fails to obtain a certificate, ensure your domain is correctly pointed to your server's IP and that no other services are using port 80 during the certificate issuance.

---

## Conclusion

You now have a simple and automated way to install SSL certificates on your server using Certbot. For more advanced configurations or troubleshooting, refer to the Certbot documentation or community support.



