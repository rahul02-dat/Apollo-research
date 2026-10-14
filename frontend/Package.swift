// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "ApolloDashboard",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "ApolloDashboard", targets: ["ApolloDashboard"])
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "ApolloDashboard",
            dependencies: [],
            path: "Sources/ApolloDashboard"
        )
    ]
)
