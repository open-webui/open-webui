import SwiftUI
import WebKit

struct WebView: NSViewRepresentable {
    let url: URL
    let reloadToken: Int

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeNSView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        if webView.url?.absoluteString != url.absoluteString {
            webView.load(URLRequest(url: url))
        } else if context.coordinator.reloadToken != reloadToken {
            context.coordinator.reloadToken = reloadToken
            webView.reload()
        }
    }

    final class Coordinator: NSObject, WKNavigationDelegate {
        var reloadToken = 0

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            guard navigationAction.navigationType == .linkActivated,
                  let url = navigationAction.request.url,
                  let currentHost = webView.url?.host,
                  url.host != currentHost
            else {
                decisionHandler(.allow)
                return
            }

            NSWorkspace.shared.open(url)
            decisionHandler(.cancel)
        }
    }
}
