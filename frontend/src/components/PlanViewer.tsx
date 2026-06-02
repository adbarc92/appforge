import ReactMarkdown from "react-markdown";

import type { Task } from "../types";

interface Props {
  adr: string | null;
  tasks: Task[];
  designSpec: Record<string, unknown> | null;
}

export function PlanViewer({ adr, tasks, designSpec }: Props) {
  return (
    <div data-testid="plan-viewer" className="space-y-4">
      {adr && (
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Architecture
          </h3>
          <div className="prose prose-sm max-w-none bg-white border rounded p-3">
            <ReactMarkdown>{adr}</ReactMarkdown>
          </div>
        </section>
      )}

      {tasks.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Tasks
          </h3>
          <div className="bg-white border rounded overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Title</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Owner</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Depends On</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tasks.map((task) => (
                  <tr key={task.id}>
                    <td className="px-3 py-2 font-medium">{task.title}</td>
                    <td className="px-3 py-2 text-gray-600">{task.owner_agent}</td>
                    <td className="px-3 py-2 text-gray-500">
                      {task.depends_on.length > 0 ? task.depends_on.join(", ") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {designSpec && (
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Design
          </h3>
          <pre className="bg-gray-50 border rounded p-3 text-xs overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(designSpec, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}
