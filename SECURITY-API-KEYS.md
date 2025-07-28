# 🔒 API Key Security Guidelines - mAI Project

**⚠️ CRITICAL: This document addresses security vulnerabilities found in the repository.**

## Security Incident Summary

**Date**: July 28, 2025  
**Issue**: OpenRouter API keys were exposed in public repository  
**Status**: ✅ **RESOLVED**  
**Key Affected**: `sk-or-v1-...e6f8` (automatically disabled by OpenRouter)

## Immediate Actions Taken

### ✅ 1. Key Exposure Eliminated
- Removed real API key from `scripts/production/clients.yaml.example`
- Replaced with placeholder: `sk-or-v1-YOUR_OPENROUTER_API_KEY_HERE_REPLACE_WITH_REAL_KEY`
- Updated documentation examples to use placeholders

### ✅ 2. Repository Security Hardened
- Added comprehensive `.gitignore` entries for API keys and secrets
- Protected patterns: `clients.yaml`, `*.key`, `**/api-keys/`, `.secrets`
- Prevents future accidental commits of sensitive data

### ✅ 3. Security Documentation Created
- This security guide for team awareness
- Clear procedures for API key management
- Best practices for development workflow

## 🚨 Critical Security Rules

### **NEVER Commit These Files/Patterns:**
```bash
# Production configuration with real API keys
clients.yaml
*.key
*.pem
**/api-keys/
openrouter_api_key*
**/secrets/
.secrets
.env (except .env.example)
```

### **Always Use These Patterns:**
```bash
# Example files with placeholders
clients.yaml.example
.env.example
README files with "sk-or-v1-YOUR_API_KEY_HERE"
```

## 🔑 Proper API Key Management

### **Development Environment**
```bash
# ✅ CORRECT - Environment variables (never committed)
export OPENROUTER_API_KEY="sk-or-v1-your-real-key-here"

# ✅ CORRECT - .env file (gitignored)
echo "OPENROUTER_API_KEY=sk-or-v1-your-real-key-here" > .env

# ❌ WRONG - Never hardcode in source files
api_key = "sk-or-v1-real-key-here"  # NEVER DO THIS
```

### **Production Deployment**
```bash
# ✅ CORRECT - Copy example and customize locally
cp clients.yaml.example clients.yaml
# Edit clients.yaml with real keys (gitignored)

# ✅ CORRECT - Docker secrets or environment injection
docker run -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" mai-app

# ❌ WRONG - Never put real keys in docker-compose.yml committed to git
```

### **Documentation**
```bash
# ✅ CORRECT - Use placeholders in docs
OPENROUTER_API_KEY=sk-or-v1-YOUR_API_KEY_HERE

# ✅ CORRECT - Reference environment setup
# See .env.example for configuration template

# ❌ WRONG - Real keys in documentation
OPENROUTER_API_KEY=sk-or-v1-1919a511cf...  # NEVER DO THIS
```

## 🛡️ Security Checklist Before Commits

**Run this checklist before every `git commit`:**

```bash
# 1. Check for exposed API keys
git diff --cached | grep -i "sk-or-v1-"
# Should return empty (no matches)

# 2. Verify .gitignore is working
git status | grep -E "(clients\.yaml|\.env)$"
# Should only show .gitignore changes, not real config files

# 3. Review staged files
git diff --cached --name-only
# Ensure no sensitive files are staged

# 4. Double-check example files
grep -r "sk-or-v1-[a-f0-9]\{64\}" . --exclude-dir=.git
# Should return empty (no real keys found)
```

## 🔧 Emergency Response Procedure

**If API key is accidentally committed:**

### **Immediate Actions (< 5 minutes):**
```bash
# 1. Disable the key immediately
# Go to https://openrouter.ai/keys and disable the exposed key

# 2. Generate new key
# Create replacement key in OpenRouter dashboard

# 3. Remove from repository immediately
git filter-branch --tree-filter 'sed -i "s/sk-or-v1-EXPOSED_KEY/sk-or-v1-PLACEHOLDER/g" filename' HEAD
# OR use BFG Repo-Cleaner for complex cases
```

### **Follow-up Actions (< 30 minutes):**
```bash
# 1. Update all deployments with new key
# 2. Force push to remove from remote history
git push --force-with-lease origin branch-name
# 3. Rotate any downstream systems using the key
# 4. Monitor for unauthorized usage
```

## 🏢 Team Guidelines

### **Code Reviews Must Check:**
- [ ] No hardcoded API keys in any files
- [ ] All example files use placeholders
- [ ] .env files are gitignored
- [ ] Configuration files use environment variables

### **Development Workflow:**
1. **Use placeholders** in all committed files
2. **Local configuration** via .env files (gitignored)
3. **Production secrets** via secure deployment methods
4. **Regular security audits** of repository

### **Onboarding New Developers:**
1. Review this security document
2. Set up local .env file (never commit)
3. Understand placeholder vs. real key distinction
4. Test security checklist procedure

## 📞 Security Contact

**For security incidents or questions:**
- **Primary**: Development Team Lead
- **Security Email**: kontakt@[domain] (mark as CONFIDENTIAL)
- **OpenRouter Support**: security@openrouter.ai

## 📚 Additional Resources

- [OpenRouter API Key Management](https://openrouter.ai/keys)
- [Git Secret Management Best Practices](https://docs.github.com/en/code-security/secret-scanning)
- [Docker Secrets Management](https://docs.docker.com/engine/swarm/secrets/)

---

**🛡️ Remember: API keys are like passwords - treat them with the same level of security!**

**Last Updated**: July 28, 2025  
**Next Review**: August 28, 2025