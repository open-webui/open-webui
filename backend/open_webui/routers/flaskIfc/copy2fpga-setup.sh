
echo " Remove the device "
sudo bash -c "echo 1 > /sys/bus/pci/devices/0000\:01\:00.0/remove"

echo "rescan"
sudo bash -c "echo 1 > /sys/bus/pci/rescan"

echo " dump the pci data"
/aws/proj/rel/sw/platform/release_v0.1.1.tsv026_04_15_2025/scripts/dump-pci.sh

echo " set the pci bit to access mem"
sudo setpci -s 0000:01:00.0 COMMAND=0x02
