import { BrowserWindow, app } from 'electron';
import { join } from 'path';
import { IPCManager } from './ipc/ipcManager';
import { getRendererPath } from './envUtils';
import { LemonadeStatus } from './ipc/ipcTypes';

const RAUX_URL = 'http://localhost:8080';
const LOADING_PAGE = getRendererPath('pages', 'loading', 'loading.html');
const PRELOAD_SCRIPT = getRendererPath('main_window', 'preload.js');

export class WindowManager {
  private static instance: WindowManager;
  private mainWindow: BrowserWindow | null = null;
  private ipcManager = IPCManager.getInstance();
  private baseTitle = 'RAUX';

  private constructor() {}

  public static getInstance(): WindowManager {
    if (!WindowManager.instance) {
      WindowManager.instance = new WindowManager();
    }
    return WindowManager.instance;
  }

  public createMainWindow(): void {
    this.mainWindow = new BrowserWindow({
      height: 1024,
      width: 1280,
      webPreferences: {
        preload: PRELOAD_SCRIPT,
        contextIsolation: true,
        nodeIntegration: false,
      },
      show: true,
    });

    this.mainWindow.setMenuBarVisibility(false);
    
    this.mainWindow.loadFile(LOADING_PAGE);
    
    this.ipcManager.registerRenderer(this.mainWindow.webContents.id, this.mainWindow.webContents);
    
    this.mainWindow.on('close', () => this.destroyIcps());
    this.mainWindow.on('closed', () => this.destroyIcps());
  }

  public showLoadingPage(): void {
    if (this.mainWindow) {
      this.mainWindow.loadFile(LOADING_PAGE);
    }
  }

  public showErrorPage(message: string): void {
    if (this.mainWindow) {
      this.mainWindow.loadURL(`data:text/html,<h1>${message}</h1>`);
    }
  }

  public showMainApp(): void {
    if (this.mainWindow) {
      this.mainWindow.loadURL(RAUX_URL);
    }
  }

  public getMainWindow(): BrowserWindow | null {
    return this.mainWindow;
  }

  public destroyIcps() {
    this.ipcManager.unregisterRenderer(this.mainWindow?.webContents.id);
    this.ipcManager.unregisterAllRenderers();
    this.mainWindow = null;
  }

  /**
   * Update window title with Lemonade status
   */
  public updateLemonadeStatus(status: LemonadeStatus): void {
    if (!this.mainWindow) {
      return;
    }

    const statusText = this.formatStatusForTitle(status);
    const newTitle = `${this.baseTitle} • ${statusText}`;
    
    this.mainWindow.setTitle(newTitle);
  }

  /**
   * Clear Lemonade status from title (show just base title)
   */
  public clearLemonadeStatus(): void {
    if (!this.mainWindow) {
      return;
    }

    this.mainWindow.setTitle(this.baseTitle);
  }

  /**
   * Format status for display in window title
   */
  private formatStatusForTitle(status: LemonadeStatus): string {
    const { status: state, isHealthy } = status;
    
    switch (state) {
      case 'running':
        return isHealthy ? '🟢 Lemonade Running' : '🟡 Lemonade Issues';
      case 'starting':
        return '🟡 Lemonade Starting';
      case 'stopped':
        return '🔴 Lemonade Stopped';
      case 'crashed':
        return '🔴 Lemonade Crashed';
      case 'unavailable':
        return '⚫ Lemonade Unavailable';
      default:
        return '❓ Lemonade Unknown';
    }
  }
} 