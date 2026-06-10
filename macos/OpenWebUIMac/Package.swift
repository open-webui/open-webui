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
        .target(
            name: "OpenWebUIMacCore",
            linkerSettings: [
                .linkedFramework("Security")
            ]
        ),
        .executableTarget(
            name: "OpenWebUIMac",
            dependencies: ["OpenWebUIMacCore"],
            linkerSettings: [
                .linkedFramework("AppKit")
            ]
        ),
        .testTarget(
            name: "OpenWebUIMacCoreTests",
            dependencies: ["OpenWebUIMacCore"]
        )
    ]
)
