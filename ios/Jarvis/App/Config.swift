import Foundation

enum Config {
    /// Base URL of the Jarvis backend.
    ///
    /// The iOS Simulator shares the Mac's network, so `localhost` works as-is
    /// against a backend run with `uvicorn app.main:app`. On a physical device,
    /// replace with your Mac's LAN IP, e.g. `http://192.168.1.20:8000`.
    static let baseURL = URL(string: "http://localhost:8000")!
}
