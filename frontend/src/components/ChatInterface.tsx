import { useState } from "react";

import { useSocket } from "../hooks/useSocket";
import { useProjectStore } from "../stores/projectStore";
import { PRDViewer } from "./PRDViewer";

export function ChatInterface() {
  const { sendMessage } = useSocket();
  const messages = useProjectStore((s) => s.messages);
  const prd = useProjectStore((s) => s.prd);
  const [draft, setDraft] = useState("");

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    useProjectStore.getState().addMessage({
      id: `${Date.now()}-user`,
      role: "user",
      text,
      timestamp: Date.now(),
    });
    sendMessage(text);
    setDraft("");
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
                m.role === "user"
                  ? "bg-blue-500 text-white"
                  : m.role === "system"
                    ? "bg-gray-200 text-gray-700 italic"
                    : "bg-white border"
              }`}
            >
              {m.agent && <div className="text-xs font-semibold mb-1">{m.agent}</div>}
              <div className="whitespace-pre-wrap">{m.text}</div>
            </div>
          </div>
        ))}
        {prd && (
          <div>
            <div className="text-xs font-semibold mb-1 text-gray-500">Draft PRD</div>
            <PRDViewer markdown={prd} />
          </div>
        )}
      </div>
      <form onSubmit={onSubmit} className="border-t p-3 flex gap-2 bg-white">
        <input
          type="text"
          role="textbox"
          className="flex-1 border rounded px-3 py-2 text-sm"
          placeholder="Describe your idea or answer a question..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
        >
          Send
        </button>
      </form>
    </div>
  );
}
