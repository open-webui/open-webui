#!/bin/bash
CONDA_BASE=$(conda info --base)
echo "CONDA_BASE:" $CONDA_BASE

# Check if conda is installed by sourcing the conda initialization script
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    . "$HOME/miniconda3/etc/profile.d/conda.sh"
    echo "Found miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    . "$HOME/anaconda3/etc/profile.d/conda.sh"
    echo "Found anaconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/opt/miniconda3/etc/profile.d/conda.sh" ]; then
    . "$HOME/opt/miniconda3/etc/profile.d/conda.sh"
    echo "Found opt/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/opt/anaconda3/etc/profile.d/conda.sh" ]; then
    . "$HOME/opt/anaconda3/etc/profile.d/conda.sh"
    echo "Found opt/anaconda3/etc/profile.d/conda.sh"
else
    echo "Conda initialization script not found. Please install Conda and ensure it is properly initialized."
    exit 1
fi