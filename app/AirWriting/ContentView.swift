import SwiftUI

/// Minimal-UI auf der Watch: Laptop-IP eingeben, Start/Stop, Status sehen.
struct ContentView: View {
    @StateObject private var streamer = MotionStreamer()

    // Voreinstellungen werden gespeichert, damit man die IP nicht jedes Mal neu tippt.
    @AppStorage("host") private var host: String = "192.168.1.42"
    @AppStorage("port") private var port: String = "8000"

    var body: some View {
        ScrollView {
            VStack(spacing: 10) {
                Text("Air-Writing")
                    .font(.headline)

                TextField("Laptop-IP", text: $host)
                    .textContentType(.URL)

                TextField("Port", text: $port)

                Button(action: toggle) {
                    Text(streamer.isStreaming ? "Stop" : "Start")
                        .frame(maxWidth: .infinity)
                }
                .tint(streamer.isStreaming ? .red : .green)

                Text(streamer.statusText)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)

                if streamer.isStreaming {
                    Text("\(streamer.sampleCount) Samples")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
            .padding()
        }
    }

    private func toggle() {
        if streamer.isStreaming {
            streamer.stop()
        } else {
            streamer.start(host: host, port: Int(port) ?? 8000)
        }
    }
}

#Preview {
    ContentView()
}
