# Open-WebUI Conda Environment Snapshot

**Date Created:** $(date)
**System:** macOS 24.4.0 (Darwin)
**Python Version:** 3.11.13
**Python Path:** /opt/anaconda3/envs/open-webui/bin/python

## Files Generated

1. **open-webui-environment.yml** - Complete conda environment export
2. **open-webui-pip-list.txt** - Detailed pip package list
3. **conda-system-info.txt** - Conda and system configuration
4. **open-webui-environment-summary.md** - This summary file

## How to Compare with Another Computer

### Option 1: Recreate Environment
```bash
# On the other computer, use the YAML file to recreate the environment
conda env create -f open-webui-environment.yml
```

### Option 2: Compare Package Lists
```bash
# Compare pip lists between computers
diff open-webui-pip-list.txt other-computer-pip-list.txt
```

### Option 3: Check for Missing Packages
```bash
# On the other computer, generate a pip list and compare
conda activate open-webui
pip list > other-computer-pip-list.txt
# Then compare the files
```

## Key Information

- **Environment Name:** open-webui
- **Conda Base:** /opt/anaconda3
- **Environment Location:** /opt/anaconda3/envs/open-webui

## Notes

- The YAML file contains all conda-installed packages with exact versions
- The pip list includes both conda and pip-installed packages
- Use the conda system info to compare conda versions and configurations
- All files are ready for transfer to another computer for comparison
