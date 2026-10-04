import SwiftUI

struct SetupView: View {
    @Environment(AppModel.self) private var model

    @State private var apiKey = ""
    @State private var error: String?
    @State private var working = false

    private var trimmedKey: String {
        apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Space.xl) {
                VStack(alignment: .leading, spacing: Theme.Space.sm) {
                    Eyebrow("Step 2")
                    DisplayTitle("Add your key", size: 40)
                }

                Text("Jarvis uses your OpenAI key to generate episodes. It's "
                     + "encrypted on the server and never shown again.")
                    .font(.system(size: 15))
                    .foregroundStyle(Theme.muted)
                    .fixedSize(horizontal: false, vertical: true)

                VStack(alignment: .leading, spacing: Theme.Space.md) {
                    Eyebrow("OpenAI API Key")
                    SecureField("sk-…", text: $apiKey)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .underlinedField()
                }

                if let error {
                    Text(error).font(.system(size: 13)).foregroundStyle(Theme.danger)
                }

                PrimaryButton(
                    title: "Save & Continue",
                    loading: working,
                    enabled: !trimmedKey.isEmpty,
                    action: save
                )

                QuietButton(title: "Sign out") { model.signOut() }
            }
            .padding(.horizontal, Theme.Space.lg)
            .padding(.vertical, Theme.Space.xl)
        }
        .screen()
    }

    private func save() {
        guard let token = model.token else { return }
        error = nil
        working = true
        Task {
            do {
                _ = try await APIClient.shared.setKeys(["openai": trimmedKey], token: token)
                await model.refresh()
            } catch {
                self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
            }
            working = false
        }
    }
}
