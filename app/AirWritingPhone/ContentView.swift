import SwiftUI

/// Air-Writing-Bedienoberflaeche auf dem iPhone: Laptop-IP eingeben,
/// Start/Stop, Status + Sample-Zaehler sehen. Streamt die iPhone-Sensoren
/// per WebSocket an das Backend (gleiches Format wie die Watch-Variante).
struct ContentView: View {
    @StateObject private var streamer = MotionStreamer()

    // Voreinstellungen werden gespeichert, damit man die IP nicht jedes Mal neu tippt.
    @AppStorage("host") private var host: String = "192.168.178.102"
    @AppStorage("port") private var port: String = "8000"

    var body: some View {
        VStack(spacing: 24) {
            Text("✍️ Air-Writing")
                .font(.largeTitle).bold()

            VStack(spacing: 12) {
                HStack {
                    Text("Laptop-IP")
                        .frame(width: 90, alignment: .leading)
                        .foregroundStyle(.secondary)
                    TextField("192.168.x.x", text: $host)
                        .textFieldStyle(.roundedBorder)
                        .keyboardType(.numbersAndPunctuation)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                }
                HStack {
                    Text("Port")
                        .frame(width: 90, alignment: .leading)
                        .foregroundStyle(.secondary)
                    TextField("8000", text: $port)
                        .textFieldStyle(.roundedBorder)
                        .keyboardType(.numberPad)
                }
            }

            Button(action: toggle) {
                Text(streamer.isStreaming ? "Stop" : "Start")
                    .font(.title2).bold()
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(streamer.isStreaming ? Color.red : Color.green)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }

            VStack(spacing: 6) {
                Text(streamer.statusText)
                    .foregroundStyle(.secondary)
                if streamer.isStreaming {
                    Text("\(streamer.sampleCount) Samples")
                        .font(.headline)
                        .monospacedDigit()
                }
            }

            Spacer()

            Text("iPhone in der Hand halten und Ziffern in die Luft schreiben — kurze Pause zwischen den Ziffern.")
                .font(.footnote)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
        }
        .padding()
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
