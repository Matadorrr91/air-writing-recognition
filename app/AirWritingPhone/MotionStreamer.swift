import Foundation
import CoreMotion
import UIKit

/// Liest die Bewegungssensoren des iPhones (userAcceleration + rotationRate)
/// mit fester Rate aus und streamt jedes Sample als JSON ueber einen WebSocket
/// an das Python-Backend auf dem Laptop.
///
/// Muss mit backend/config.py uebereinstimmen:
///   - SAMPLE_RATE_HZ
///   - Kanal-Reihenfolge / Feldnamen: t, ax, ay, az, gx, gy, gz
///
/// Identisches Datenformat wie die Watch-Variante -> Backend-Endpunkt /ws/watch.
final class MotionStreamer: ObservableObject {

    // MARK: - Konfiguration
    static let sampleRateHz: Double = 50          // == config.SAMPLE_RATE_HZ
    static let wsPath = "/ws/watch"

    // MARK: - UI-Status
    @Published var isStreaming = false
    @Published var statusText = "bereit"
    @Published var sampleCount = 0

    private let motionManager = CMMotionManager()
    private let queue = OperationQueue()
    private var task: URLSessionWebSocketTask?

    /// Startet die Verbindung zu ws://<host>:<port>/ws/watch und beginnt zu streamen.
    func start(host: String, port: Int) {
        guard !isStreaming else { return }
        guard motionManager.isDeviceMotionAvailable else {
            statusText = "Sensoren nicht verfuegbar"
            return
        }
        guard let url = URL(string: "ws://\(host):\(port)\(Self.wsPath)") else {
            statusText = "ungueltige Adresse"
            return
        }

        let session = URLSession(configuration: .default)
        task = session.webSocketTask(with: url)
        task?.resume()
        receiveLoop()                 // Socket gesund halten

        sampleCount = 0
        // Bildschirm waehrend des Streamens anlassen
        UIApplication.shared.isIdleTimerDisabled = true

        motionManager.deviceMotionUpdateInterval = 1.0 / Self.sampleRateHz
        motionManager.startDeviceMotionUpdates(to: queue) { [weak self] motion, _ in
            guard let self, let m = motion else { return }
            self.send(motion: m)
        }

        isStreaming = true
        statusText = "streamt → \(host):\(port)"
    }

    func stop() {
        motionManager.stopDeviceMotionUpdates()
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        isStreaming = false
        statusText = "gestoppt"
        UIApplication.shared.isIdleTimerDisabled = false
    }

    // MARK: - Senden
    private func send(motion m: CMDeviceMotion) {
        let a = m.userAcceleration       // g, Schwerkraft bereits entfernt
        let g = m.rotationRate           // rad/s
        // Kompaktes JSON ohne Encoder-Overhead (50x pro Sekunde).
        let json = String(
            format: "{\"t\":%.4f,\"ax\":%.5f,\"ay\":%.5f,\"az\":%.5f,\"gx\":%.5f,\"gy\":%.5f,\"gz\":%.5f}",
            m.timestamp, a.x, a.y, a.z, g.x, g.y, g.z
        )
        task?.send(.string(json)) { [weak self] error in
            if let error {
                DispatchQueue.main.async {
                    self?.statusText = "Sendefehler: \(error.localizedDescription)"
                }
            }
        }
        DispatchQueue.main.async { self.sampleCount += 1 }
    }

    /// WebSocket erwartet, dass empfangen wird, sonst kann er blockieren.
    private func receiveLoop() {
        task?.receive { [weak self] result in
            switch result {
            case .failure:
                break
            case .success:
                self?.receiveLoop()
            }
        }
    }
}
