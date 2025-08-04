#! /bin/bash
# This file runs the PCIE setup needed for file transfer.
# Also, it invokes the file transfer utility: copy2fpga-x86
# Note: sudo permissions are needed for file transfer
# 
#echo "  Inside copy2fpga-x86.sh "
#sudo ./copy2fpga-setup.sh
echo "sudo ./copy2fpga-x86 $1"
sleep 5
sudo ./copy2fpga-x86 $1
