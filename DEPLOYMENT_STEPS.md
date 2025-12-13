# Mermaid Scalability - Deployment Steps

## ✅ Completed
- [x] Code implementation
- [x] Test suite created
- [x] Changes committed to git
- [x] Pushed to GitHub

## Next Steps for Deployment

### 1. Build the Application

**Yes, you need to build after pushing to GitHub.**

```bash
# Build the frontend
npm run build
```

This will:
- Compile Svelte components
- Bundle JavaScript/CSS
- Generate production-ready assets
- Include the new Mermaid optimization code

### 2. Verify Build Success

```bash
# Check for build errors
npm run build 2>&1 | grep -i error

# If successful, you should see:
# - Build completed
# - No TypeScript errors
# - Assets generated in .svelte-kit/
```

### 3. Test Locally (Optional but Recommended)

```bash
# Start dev server to verify
npm run dev

# Test Mermaid rendering:
# 1. Open browser
# 2. Create a chat with Mermaid diagram
# 3. Verify diagram renders
# 4. Check browser console for Mermaid logs
# 5. Verify cache is working (second render should be instant)
```

### 4. Deploy to OpenShift

#### Option A: If using BuildConfig (Automatic)
```bash
# Push triggers automatic build
# Monitor build:
oc get builds -n rit-genai-naga-dev --watch

# Check build logs:
oc logs -f build/<build-name> -n rit-genai-naga-dev
```

#### Option B: If using Manual Build
```bash
# Build Docker image
docker build -t your-registry/mermaid-optimized:latest .

# Push to registry
docker push your-registry/mermaid-optimized:latest

# Update deployment
oc set image deployment/open-webui open-webui=your-registry/mermaid-optimized:latest -n rit-genai-naga-dev
```

### 5. Verify Deployment

After deployment, verify:

1. **Application starts successfully**
   ```bash
   oc get pods -n rit-genai-naga-dev
   oc logs -f deployment/open-webui -n rit-genai-naga-dev
   ```

2. **Mermaid rendering works**
   - Open application in browser
   - Create/test Mermaid diagram
   - Check browser console for:
     - `[Mermaid] Global initialization successful`
     - `[Mermaid] Cache hit` (on second render)
     - `[Mermaid] Render completed`

3. **Performance metrics**
   - Open browser DevTools → Console
   - Look for Mermaid performance logs
   - Verify cache hit rate > 70% after warmup

### 6. Monitor (First 24 Hours)

Watch for:
- ✅ Mermaid diagrams rendering correctly
- ✅ Cache working (faster second renders)
- ✅ No console errors
- ✅ Memory usage stable
- ✅ IndexedDB persisting across refreshes

### 7. Rollback Plan (If Needed)

If issues occur:

```bash
# Rollback to previous deployment
oc rollout undo deployment/open-webui -n rit-genai-naga-dev

# Or revert git commit
git revert HEAD
git push
# Rebuild and redeploy
```

## Environment Variables

No new environment variables required. All configuration is in code:
- `MERMAID_CONFIG` in `src/lib/constants.ts`
- Can be adjusted if needed

## Configuration Tuning (Optional)

If needed, adjust in `src/lib/constants.ts`:

```typescript
export const MERMAID_CONFIG = {
  MEMORY_CACHE_SIZE: 100,        // Adjust cache size
  INDEXEDDB_MAX_SIZE: 5 * 1024 * 1024,  // Adjust IndexedDB limit
  DEBOUNCE_DELAY: 300,           // Adjust debounce timing
  // ... other settings
};
```

## Troubleshooting

### If Mermaid doesn't render:
1. Check browser console for errors
2. Verify Mermaid 11.12.2 is installed: `npm list mermaid`
3. Check service initialization: Look for `[Mermaid] Global initialization` log

### If cache not working:
1. Check IndexedDB in DevTools → Application → IndexedDB
2. Verify `mermaid_cache_db` exists
3. Check console for cache hit/miss logs

### If performance issues:
1. Check metrics logs: `[Mermaid] Metrics: ...`
2. Verify cache hit rate
3. Check render times in console

## Success Criteria

✅ Deployment successful when:
- Application starts without errors
- Mermaid diagrams render correctly
- Cache works (second render is instant)
- No console errors
- Performance metrics show improvement

## Summary

**Order of Operations:**
1. ✅ Code pushed to GitHub
2. **→ Build application** (`npm run build`)
3. **→ Deploy to OpenShift** (via BuildConfig or manual)
4. **→ Verify deployment** (check logs, test rendering)
5. **→ Monitor** (first 24 hours)

**Build is required** - The new code needs to be compiled before deployment.

