import SwiftUI

struct TopicsView: View {
    @Environment(AppModel.self) private var model

    @State private var topics: [String] = []
    @State private var newTopic = ""
    @State private var error: String?
    @State private var working = false

    private var trimmedNew: String {
        newTopic.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Space.xl) {
                VStack(alignment: .leading, spacing: Theme.Space.sm) {
                    Eyebrow("Step 1")
                    DisplayTitle("What should Jarvis cover?", size: 36)
                }

                Text("Add a few topics. Each morning we'll generate short episodes "
                     + "from them. You can change these anytime.")
                    .font(.system(size: 15))
                    .foregroundStyle(Theme.muted)
                    .fixedSize(horizontal: false, vertical: true)

                addField

                if !topics.isEmpty {
                    VStack(spacing: 0) {
                        ForEach(topics, id: \.self) { topic in
                            topicRow(topic)
                        }
                    }
                }

                if let error {
                    Text(error).font(.system(size: 13)).foregroundStyle(Theme.danger)
                }

                PrimaryButton(
                    title: "Continue",
                    loading: working,
                    enabled: !topics.isEmpty,
                    action: save
                )

                QuietButton(title: "Sign out") { model.signOut() }
            }
            .padding(.horizontal, Theme.Space.lg)
            .padding(.vertical, Theme.Space.xl)
        }
        .screen()
        .onAppear {
            if topics.isEmpty, let existing = model.profile?.topics {
                topics = existing
            }
        }
    }

    private var addField: some View {
        HStack(alignment: .firstTextBaseline, spacing: Theme.Space.md) {
            TextField("Add a topic", text: $newTopic)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .submitLabel(.done)
                .onSubmit(addTopic)
            Button("Add", action: addTopic)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(trimmedNew.isEmpty ? Theme.faint : Theme.ink)
                .disabled(trimmedNew.isEmpty)
        }
        .underlinedField()
    }

    private func topicRow(_ topic: String) -> some View {
        VStack(spacing: 0) {
            HStack {
                Text(topic)
                    .font(.system(size: 17))
                    .foregroundStyle(Theme.ink)
                Spacer()
                Button {
                    topics.removeAll { $0 == topic }
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Theme.muted)
                }
            }
            .padding(.vertical, Theme.Space.md)
            Hairline()
        }
    }

    private func addTopic() {
        let value = trimmedNew
        guard !value.isEmpty,
              !topics.contains(where: { $0.caseInsensitiveCompare(value) == .orderedSame })
        else {
            newTopic = ""
            return
        }
        topics.append(value)
        newTopic = ""
    }

    private func save() {
        guard let token = model.token else { return }
        error = nil
        working = true
        Task {
            do {
                _ = try await APIClient.shared.setTopics(topics, token: token)
                await model.refresh()
            } catch {
                self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
            }
            working = false
        }
    }
}
