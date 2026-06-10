import AppKit
import SwiftUI

@main
enum OpenWebUIMacMain {
    @MainActor
    static func main() {
        let application = NSApplication.shared
        let delegate = AppDelegate()
        AppDelegateRetainer.shared = delegate

        application.delegate = delegate
        application.setActivationPolicy(.regular)
        application.finishLaunching()
        delegate.configureMainMenu()
        delegate.showMainWindow()
        application.activate(ignoringOtherApps: true)
        application.run()
    }
}

@MainActor
private enum AppDelegateRetainer {
    static var shared: AppDelegate?
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private let appState = AppState()
    private var window: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApplication.shared.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        appState.stopForQuitIfNeeded()
        return .terminateNow
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag {
            showMainWindow()
        }
        return true
    }

    func showMainWindow() {
        if let window {
            window.makeKeyAndOrderFront(nil)
            return
        }

        let rootView = ContentView()
            .environmentObject(appState)

        let visibleFrame = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1200, height: 820)
        let windowWidth = min(1200, max(900, visibleFrame.width - 80))
        let windowHeight = min(820, max(680, visibleFrame.height - 80))

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: windowWidth, height: windowHeight),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Open WebUI"
        window.contentViewController = NSHostingController(rootView: rootView)
        window.setFrameOrigin(NSPoint(x: 40, y: 80))
        window.makeKeyAndOrderFront(nil)
        self.window = window
    }

    func configureMainMenu() {
        let mainMenu = NSMenu()
        mainMenu.addItem(appMenuItem())
        mainMenu.addItem(editMenuItem())
        mainMenu.addItem(serviceMenuItem())
        NSApplication.shared.mainMenu = mainMenu
    }

    private func appMenuItem() -> NSMenuItem {
        let menuItem = NSMenuItem()
        let menu = NSMenu(title: "Open WebUI")
        menu.addItem(
            withTitle: "Quit Open WebUI",
            action: #selector(NSApplication.terminate(_:)),
            keyEquivalent: "q"
        )
        menuItem.submenu = menu
        return menuItem
    }

    private func editMenuItem() -> NSMenuItem {
        let menuItem = NSMenuItem()
        let menu = NSMenu(title: "Edit")
        menu.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        menu.addItem(NSMenuItem.separator())
        menu.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        menu.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        menu.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        menu.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        menuItem.submenu = menu
        return menuItem
    }

    private func serviceMenuItem() -> NSMenuItem {
        let menuItem = NSMenuItem()
        let menu = NSMenu(title: "Service")

        let restart = NSMenuItem(
            title: "Restart Service",
            action: #selector(restartService),
            keyEquivalent: "R"
        )
        restart.keyEquivalentModifierMask = [.command, .shift]
        restart.target = self
        menu.addItem(restart)

        let stop = NSMenuItem(
            title: "Stop Managed Service",
            action: #selector(stopManagedService),
            keyEquivalent: "S"
        )
        stop.keyEquivalentModifierMask = [.command, .shift]
        stop.target = self
        menu.addItem(stop)

        menu.addItem(NSMenuItem.separator())

        let browser = NSMenuItem(
            title: "Open in Browser",
            action: #selector(openInBrowser),
            keyEquivalent: "B"
        )
        browser.keyEquivalentModifierMask = [.command, .shift]
        browser.target = self
        menu.addItem(browser)

        menuItem.submenu = menu
        return menuItem
    }

    @objc private func restartService() {
        appState.restart()
    }

    @objc private func stopManagedService() {
        appState.service.stop()
    }

    @objc private func openInBrowser() {
        NSWorkspace.shared.open(appState.settingsStore.settings.rootURL)
    }
}
