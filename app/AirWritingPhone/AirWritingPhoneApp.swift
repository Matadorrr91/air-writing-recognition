import SwiftUI

/// Minimaler iPhone-Begleiter. Dient nur als "Traeger", damit watchOS die
/// Watch-App akzeptiert und installiert. Die eigentliche Funktion (Sensoren
/// streamen) laeuft auf der Apple Watch.
@main
struct AirWritingPhoneApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
