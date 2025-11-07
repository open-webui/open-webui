#!/usr/bin/env node

/**
 * Python 3.12 Setup Script for Tauri Desktop App
 * 
 * This script downloads and prepares Python 3.12 standalone builds
 * for bundling with the Tauri application.
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

const PYTHON_VERSION = '3.12.7';
const RESOURCES_DIR = path.join(__dirname, '..', 'src-tauri', 'resources', 'python');

// Python Build Standalone releases
const PYTHON_URLS = {
  darwin: {
    arm64: `https://github.com/indygreg/python-build-standalone/releases/download/20241016/cpython-${PYTHON_VERSION}+20241016-aarch64-apple-darwin-install_only.tar.gz`,
    x64: `https://github.com/indygreg/python-build-standalone/releases/download/20241016/cpython-${PYTHON_VERSION}+20241016-x86_64-apple-darwin-install_only.tar.gz`
  },
  win32: {
    x64: `https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-amd64.zip`
  },
  linux: {
    x64: `https://github.com/indygreg/python-build-standalone/releases/download/20241016/cpython-${PYTHON_VERSION}+20241016-x86_64-unknown-linux-gnu-install_only.tar.gz`
  }
};

function getPlatformInfo() {
  const platform = os.platform();
  const arch = os.arch();
  
  let platformName, archName;
  
  if (platform === 'darwin') {
    platformName = 'macos';
    archName = arch === 'arm64' ? 'arm64' : 'x64';
  } else if (platform === 'win32') {
    platformName = 'windows';
    archName = 'x64';
  } else if (platform === 'linux') {
    platformName = 'linux';
    archName = 'x64';
  } else {
    throw new Error(`Unsupported platform: ${platform}`);
  }
  
  return { platformName, archName, platform };
}

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    console.log(`Downloading from: ${url}`);
    console.log(`Saving to: ${dest}`);
    
    const file = fs.createWriteStream(dest);
    
    https.get(url, (response) => {
      if (response.statusCode === 302 || response.statusCode === 301) {
        // Handle redirect
        return downloadFile(response.headers.location, dest).then(resolve).catch(reject);
      }
      
      if (response.statusCode !== 200) {
        reject(new Error(`Failed to download: ${response.statusCode}`));
        return;
      }
      
      const totalSize = parseInt(response.headers['content-length'], 10);
      let downloadedSize = 0;
      let lastPercent = 0;
      
      response.on('data', (chunk) => {
        downloadedSize += chunk.length;
        const percent = Math.floor((downloadedSize / totalSize) * 100);
        if (percent !== lastPercent && percent % 10 === 0) {
          console.log(`Progress: ${percent}%`);
          lastPercent = percent;
        }
      });
      
      response.pipe(file);
      
      file.on('finish', () => {
        file.close();
        console.log('Download complete!');
        resolve();
      });
    }).on('error', (err) => {
      fs.unlink(dest, () => {});
      reject(err);
    });
  });
}

function extractArchive(archivePath, destDir) {
  console.log(`Extracting ${archivePath} to ${destDir}...`);
  
  const ext = path.extname(archivePath);
  
  try {
    if (ext === '.gz') {
      // Extract tar.gz
      execSync(`tar -xzf "${archivePath}" -C "${destDir}"`, { stdio: 'inherit' });
    } else if (ext === '.zip') {
      // Extract zip
      execSync(`unzip -q "${archivePath}" -d "${destDir}"`, { stdio: 'inherit' });
    }
    
    console.log('Extraction complete!');
  } catch (error) {
    throw new Error(`Failed to extract archive: ${error.message}`);
  }
}

async function setupPython() {
  console.log('=== Python 3.12 Setup for Tauri Desktop App ===\n');
  
  const { platformName, archName, platform } = getPlatformInfo();
  console.log(`Platform: ${platformName} (${archName})`);
  
  const platformDir = path.join(RESOURCES_DIR, platformName);
  const url = PYTHON_URLS[platform][archName];
  
  if (!url) {
    throw new Error(`No Python build available for ${platformName} ${archName}`);
  }
  
  // Create directories
  if (!fs.existsSync(platformDir)) {
    fs.mkdirSync(platformDir, { recursive: true });
  }
  
  const filename = path.basename(url);
  const downloadPath = path.join(platformDir, filename);
  
  // Check if already downloaded
  if (fs.existsSync(downloadPath)) {
    console.log('\nPython archive already exists. Skipping download.');
  } else {
    console.log('\nDownloading Python 3.12...');
    await downloadFile(url, downloadPath);
  }
  
  // Extract
  console.log('\nExtracting Python...');
  extractArchive(downloadPath, platformDir);
  
  // Verify installation
  const pythonExe = platform === 'win32' ? 'python.exe' : 'bin/python3';
  let pythonPath;
  
  // Find the python executable
  if (platform === 'darwin' || platform === 'linux') {
    // For standalone builds, the structure is: python/install/bin/python3
    const installDir = fs.readdirSync(platformDir).find(dir => dir.startsWith('python'));
    if (installDir) {
      pythonPath = path.join(platformDir, installDir, pythonExe);
    }
  } else {
    pythonPath = path.join(platformDir, pythonExe);
  }
  
  if (pythonPath && fs.existsSync(pythonPath)) {
    console.log(`\n✅ Python 3.12 successfully set up at: ${pythonPath}`);
    
    // Make executable on Unix-like systems
    if (platform !== 'win32') {
      execSync(`chmod +x "${pythonPath}"`, { stdio: 'inherit' });
    }
    
    // Test Python
    try {
      const version = execSync(`"${pythonPath}" --version`, { encoding: 'utf-8' });
      console.log(`✅ Python version: ${version.trim()}`);
    } catch (error) {
      console.warn('⚠️  Could not verify Python version');
    }
  } else {
    console.warn('⚠️  Python executable not found at expected location');
  }
  
  console.log('\n=== Setup Complete ===');
  console.log('\nNext steps:');
  console.log('1. Run: npm run build');
  console.log('2. Run: npm run tauri:build');
}

// Run setup
setupPython().catch((error) => {
  console.error('\n❌ Error during setup:', error.message);
  process.exit(1);
});
