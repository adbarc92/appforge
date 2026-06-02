import { useEffect } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useParams } from "react-router-dom";

import { BudgetMeter } from "./components/BudgetMeter";
import { ChatInterface } from "./components/ChatInterface";
import { GraphCanvas } from "./components/GraphCanvas";
import { useSocket } from "./hooks/useSocket";
import { useProjectStore } from "./stores/projectStore";

function NewProject() {
  const { startProject } = useSocket();
  const navigate = useNavigate();
  const projectId = useProjectStore((s) => s.projectId);

  useEffect(() => {
    if (projectId) navigate(`/project/${projectId}`);
  }, [projectId, navigate]);

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const idea = (form.elements.namedItem("idea") as HTMLInputElement).value.trim();
    if (!idea) return;
    useProjectStore.setState({ idea });
    startProject(idea);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <form
        onSubmit={onSubmit}
        className="max-w-xl w-full space-y-4 bg-white p-8 rounded shadow"
      >
        <h1 className="text-2xl font-semibold">DevTeam.AI</h1>
        <p className="text-sm text-gray-600">
          Describe the thing you want to build. The Clarifying PM will ask up
          to 6 questions and produce a PRD.
        </p>
        <input
          name="idea"
          type="text"
          className="w-full border rounded px-3 py-2"
          placeholder='e.g. "Build me a todo app"'
          required
        />
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
        >
          Start
        </button>
      </form>
    </div>
  );
}

function ProjectWorkspace() {
  const { projectId: urlId } = useParams<{ projectId: string }>();
  const { loadProject } = useSocket();
  const storeId = useProjectStore((s) => s.projectId);

  useEffect(() => {
    if (urlId && urlId !== storeId) {
      loadProject(urlId);
    }
  }, [urlId, storeId, loadProject]);

  return (
    <div className="flex flex-col h-screen">
      <BudgetMeter />
      <div className="flex-1 grid grid-cols-2 min-h-0">
        <div className="border-r bg-gray-50"><ChatInterface /></div>
        <div className="bg-white"><GraphCanvas /></div>
      </div>
    </div>
  );
}

export default function App() {
  // Call once at top level so the singleton socket + listeners exist.
  useSocket();
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<NewProject />} />
        <Route path="/project/:projectId" element={<ProjectWorkspace />} />
      </Routes>
    </BrowserRouter>
  );
}
