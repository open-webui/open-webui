#!/bin/bash
# Cleanup script to prepare droplet for imaging
# Removes sensitive data and prepares for first boot
# Called by Packer at end of build

set -euo pipefail

echo "=== Cleaning up for image creation ==="

# Remove SSH host keys (will regenerate on first boot)
echo "Removing SSH host keys"
rm -f /etc/ssh/ssh_host_*

# Remove machine-id (will regenerate)
echo "Clearing machine-id"
truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id

# Clear bash history
echo "Clearing bash history"
history -c
> ~/.bash_history
if [ -d /home/qbmgr ]; then
    > /home/qbmgr/.bash_history
    chown qbmgr:qbmgr /home/qbmgr/.bash_history
fi

# Clear logs
echo "Truncating log files"
find /var/log -type f -exec truncate -s 0 {} \;

# Remove cloud-init artifacts (will re-run on first boot if needed)
echo "Cleaning cloud-init"
cloud-init clean --logs --seed || true

# Remove root's authorized_keys (added per-droplet)
echo "Removing root authorized_keys"
> /root/.ssh/authorized_keys || true

# Ensure qbmgr's authorized_keys is empty (added per-droplet)
if [ -d /home/qbmgr/.ssh ]; then
    echo "Clearing qbmgr authorized_keys"
    > /home/qbmgr/.ssh/authorized_keys
    chmod 600 /home/qbmgr/.ssh/authorized_keys
    chown qbmgr:qbmgr /home/qbmgr/.ssh/authorized_keys
fi

# Clean apt cache
echo "Cleaning apt cache"
apt-get clean
rm -rf /var/lib/apt/lists/*

# Remove temporary files
echo "Removing temporary files"
rm -rf /tmp/*
rm -rf /var/tmp/*

# Remove any .bash_logout that might interfere
echo "Cleaning bash logout files"
rm -f /root/.bash_logout
rm -f /home/qbmgr/.bash_logout

# Sync filesystem
echo "Syncing filesystem"
sync

echo "=== Cleanup complete ==="
echo "Image is ready for snapshotting"
