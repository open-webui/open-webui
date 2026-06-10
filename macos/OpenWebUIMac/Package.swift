// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "OpenWebUIMac",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "OpenWebUIMac", targets: ["OpenWebUIMac"])
    ],
    targets: [
        .target(name: "OpenWebUIMacCore"),
        .executableTarget(
            name: "OpenWebUIMac",
            dependencies: ["OpenWebUIMacCore"],
            linkerSettings: [
                .linkedFramework("AppKit"),
                .linkedFramework("WebKit")
            ]
        ),
        .testTarget(
            name: "OpenWebUIMacCoreTests",
            dependencies: ["OpenWebUIMacCore"]
        )
    ]
)
