# Patches for Open WebUI Customization

## Applying Patches

### All patches at once:
```bash
for patch in patches/*.patch; do
    git apply "$patch"
done
```

### Individual patch:
```bash
git apply patches/001-xynthor-branding.patch
```

## List of Patches

### 001-xynthor-branding.patch
- Change favicon to https://chatbot.xynthor.com/favicon.ico
- Change app name to XYNTHOR AI
- Update meta tags

### 002-navbar-branding.patch (needs to be created)
To create:
1. Find the Navbar.svelte file
2. Replace "Open WebUI" with "XYNTHOR AI"
3. Replace the logo
4. Create patch: `git diff > patches/002-navbar-branding.patch`

### 003-manifest-branding.patch (needs to be created)
For PWA manifest updates

## Checking Patches

Before applying:
```bash
git apply --check patches/001-xynthor-branding.patch
```

## Reverting Patches

```bash
git apply -R patches/001-xynthor-branding.patch
```