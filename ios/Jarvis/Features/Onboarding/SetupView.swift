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
        NavigationStack {
            Form {
                Section {
                    Text("Add your OpenAI API key so Jarvis can generate episodes. "
                         + "It's encrypted on the server and never shown again.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                Section("OpenAI API Key") {
                    SecureField("sk-…", text: $apiKey)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }

                if let error {
                    Text(error)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }

                Section {
                    Button(action: save) {
                        HStack {
                            Spacer()
                            if working { ProgressView() } else { Text("Save & Continue").bold() }
                            Spacer()
                        }
                    }
                    .disabled(trimmedKey.isEmpty || working)
                }

                Section {
                    Button("Sign out", role: .destructive) { model.signOut() }
                }
            }
            .navigationTitle("Almost there")
        }
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
