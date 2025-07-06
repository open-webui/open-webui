# Open WebUI Custom Build for XYNTHORAI System

This directory contains the customized Open WebUI fork integrated with the XYNTHORAI(Data Policy Layer) middleware system.

## 📁 Directory Structure

```
xynthorai-open-webui/
├── CUSTOM_BUILD.md          # Build instructions for XYNTHORAI integration
├── SETUP_COMPLETE.md        # Fork setup confirmation
├── FIX_REMOTES.md          # Git remote configuration
├── FORK_SAFETY_GUIDE.md    # Safe fork management
├── USAGE_GUIDE.md          # Custom usage instructions
├── SOLUTION_SUMMARY.md     # XYNTHORAI integration overview
├── NEXT_STEPS.md           # Future development plans
├── UPDATE_GUIDE.md         # Update procedures
├── patches/                # Custom patches and modifications
│   ├── README.md          # Patch management guide
│   └── STYLE_PATCHING_GUIDE.md  # UI customization
└── custom-config/         # Custom configurations
    └── favicon-setup.md   # Favicon customization
```

## 🔧 Custom Modifications

This fork includes:
- XynthorAI middleware integration
- Custom authentication flow with Keycloak
- OpenRouter model support
- Policy checking before LLM requests
- Custom branding (XYNTHOR AI)

## 📚 Important Documents

- **[CUSTOM_BUILD.md](CUSTOM_BUILD.md)** - How to build with XYNTHORAIfeatures
- **[FORK_SAFETY_GUIDE.md](FORK_SAFETY_GUIDE.md)** - Maintain fork safely
- **[patches/README.md](patches/README.md)** - Apply custom patches

## 🚀 Quick Commands

```bash
# Build custom image
docker build -t xynthorai-open-webui:custom .

# Apply patches
cd patches
./apply-patches.sh

# Update from upstream
git fetch upstream
git merge upstream/main
```

## ⚠️ Note

Standard Open WebUI documentation has been removed. For Open WebUI docs, see:
- https://github.com/open-webui/open-webui

For DPL-specific documentation, see:
- [Main project docs](/docs)