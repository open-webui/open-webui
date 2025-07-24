
#!/bin/bash

SEARCH_STRING1="Altera Corporation Device 0000"
SEARCH_STRING2="BittWare, Inc. Device 0076"

find_pci_device() {
    local search_string1="$1"
    local search_string2="$2"

    local bdf=$(lspci | grep -i "$search_string1" | head -1 | cut -d' ' -f1)

    if [ -z "$bdf" ]; then
        bdf=$(lspci | grep -i "$search_string2" | head -1 | cut -d' ' -f1)
    fi

    echo "$bdf"
}

PCI_BDF=$(find_pci_device "$SEARCH_STRING1" "$SEARCH_STRING2")

if [ -z "$PCI_BDF" ]; then
    exit 1
fi

MEM_ADDR=$(lspci -vvvnns "$PCI_BDF" | \
    grep -i "Region" | grep -i "Memory at" | grep -i "size=1M" | \
    sed -n 's/.*Memory at \([0-9a-fA-F]*\).*/\1/p' | head -n 1)

if [ -n "$MEM_ADDR" ]; then
    echo "$MEM_ADDR"
else
    exit 1
fi
