import { useState } from "react";

import { useSocket } from "../hooks/useSocket";
import { useProjectStore } from "../stores/projectStore";
import { PRDViewer } from "./PRDViewer";

function parseCommand(text: string): { cmd: string; arg?: string } | null {
  if (!text.startsWith("/")) return null;
  const space = text.indexOf(" ");
  if (space === -1) return { cmd: text.slice(1) };
  return { cmd: text.slice(1, space), arg: text.slice(space + 1).trim() };
}

export function ChatInterface() {
  const { sendMessage, approve, reject, modify, retry } = useSocket();
  const messages = useProjectStore((s) => s.messages);
  const prd = useProjectStore((s) => s.prd);
  const approvalPending = useProjectStore((s) => s.approvalPending);
  const [draft, setDraft] = useState("");
  const [modifyDraft, setModifyDraft] = useState("");
  const [showModify, setShowModify] = useState(false);

  const submit = (text: string) => {
    const cmd = parseCommand(text);
    if (cmd) {
      if (cmd.cmd === "approve") return approve(cmd.arg);
      if (cmd.cmd === "reject") return reject(cmd.arg);
      if (cmd.cmd === "modify" && cmd.arg) return modify(cmd.arg);
      if (cmd.cmd === "retry") return retry();
    }
    useProjectStore.getState().addMessage({
      id: `${Date.now()}-user`,
      role: "user",
      text,
      timestamp: Date.now(),
    });
    sendMessage(text);
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    submit(text);
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
        {approvalPending && (
          <div className="bg-yellow-50 border border-yellow-300 rounded p-3 space-y-2">
            <div className="font-semibold text-sm">Approval needed</div>
            {approvalPending.escalation && (
              <div className="text-xs text-red-700">Escalation: 3 rejections so far.</div>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => approve()}
                className="px-3 py-1 bg-green-600 text-white text-sm rounded"
              >
                Approve
              </button>
              <button
                type="button"
                onClick={() => reject()}
                className="px-3 py-1 bg-red-600 text-white text-sm rounded"
              >
                Reject
              </button>
              <button
                type="button"
                onClick={() => setShowModify((v) => !v)}
                className="px-3 py-1 bg-blue-600 text-white text-sm rounded"
              >
                Modify
              </button>
            </div>
            {showModify && (
              <div className="flex gap-2">
                <input
                  type="text"
                  className="flex-1 border rounded px-2 py-1 text-sm"
                  placeholder="What should be changed?"
                  value={modifyDraft}
                  onChange={(e) => setModifyDraft(e.target.value)}
                />
                <button
                  type="button"
                  className="px-3 py-1 bg-blue-700 text-white text-sm rounded"
                  onClick={() => {
                    if (modifyDraft.trim()) {
                      modify(modifyDraft.trim());
                      setModifyDraft("");
                      setShowModify(false);
                    }
                  }}
                >
                  Send
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      <form onSubmit={onSubmit} className="border-t p-3 flex gap-2 bg-white">
        <input
          type="text"
          role="textbox"
          className="flex-1 border rounded px-3 py-2 text-sm"
          placeholder="Describe your idea, answer a question, or type /approve /reject /modify ..."
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
