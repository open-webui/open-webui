#!/bin/bash

# === Extract short hostname (before the first dot) ===
SYSTEM_NAME=$(echo "$HOSTNAME" | cut -d. -f1)
echo "======================================"
echo " Running on system: $SYSTEM_NAME"
echo "======================================"

# === Check if system is supported ===
SEARCH_STRING1="Altera Corporation Device 0000"
SEARCH_STRING2="BittWare, Inc. Device 0076"

case "$SYSTEM_NAME" in
	fpga1|fpga2)
	echo "Valid system.. continuing setup"
        ;;
	fpga3|fpga4)
	echo "Valid system.. continuing setup"
        ;;
  	*)
	echo "Unknown system: $SYSTEM_NAME"
        exit 1
        ;;
esac


# === Function to find PCI device BDF based on device strings ===
find_pci_device() {
    local search_string1="$1"
    local search_string2="$2"

    local bdf=$(lspci | grep -i "$search_string1" | head -1 | cut -d' ' -f1)

    if [ -z "$bdf" ]; then
        bdf=$(lspci | grep -i "$search_string2" | head -1 | cut -d' ' -f1)
    fi

    echo "$bdf"
}

# === Define search strings ===

# === Find PCI device ===
PCI_BDF=$(find_pci_device "$SEARCH_STRING1" "$SEARCH_STRING2")

if [ -z "$PCI_BDF" ]; then
    echo "Error: Could not find PCI device matching either '$SEARCH_STRING1' or '$SEARCH_STRING2'"
    echo "Available PCI devices:"
    lspci
    exit 1
fi

# === Construct full PCI device address ===
PCI_DEVICE="0000:$PCI_BDF"
echo "Found PCI device at BDF: $PCI_DEVICE"

# === Set dump script path ===
DUMP_SCRIPT="/aws/proj/rel/sw/platform/release_v0.1.1.tsv026_04_15_2025/scripts/dump-pci.sh"

# === Remove the device ===
echo "Removing PCI device: $PCI_DEVICE"
sudo bash -c "echo 1 > /sys/bus/pci/devices/$PCI_DEVICE/remove"

# === Rescan PCI bus ===
echo "Rescanning PCI bus..."
sudo bash -c "echo 1 > /sys/bus/pci/rescan"

# === Dump PCI data ===
echo "Dumping PCI data using script: $DUMP_SCRIPT"
bash "$DUMP_SCRIPT"

# === Set PCI command bit to access memory ===
echo "Setting PCI command bit for device: $PCI_DEVICE"
sudo setpci -s "$PCI_DEVICE" COMMAND=0x02

