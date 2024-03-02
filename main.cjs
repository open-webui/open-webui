const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: true,
        },
    });


    // Load a remote URL
    mainWindow.loadURL('http://127.0.0.1:8080')



    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Start the server process when the Electron app is ready
    startServer();
}

function startServer() {
    const serverProcess = spawn('uvicorn', ['main:app', '--host', '0.0.0.0', '--port', 8080, '--forwarded-allow-ips', '*'], {
        cwd: path.join(__dirname, 'backend'), // Adjust the path to your server directory
        stdio: 'inherit',
    });

    serverProcess.on('close', (code) => {
        console.log(`Server process exited with code ${code}`);
    });
}

app.on('ready', createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (mainWindow === null) {
        createWindow();
    }
});
