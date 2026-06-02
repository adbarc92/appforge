import ReactMarkdown from "react-markdown";

interface Props { markdown: string }

export function PRDViewer({ markdown }: Props) {
  return (
    <div
      data-testid="prd-viewer"
      className="prose prose-sm max-w-none bg-white border rounded p-3"
    >
      <ReactMarkdown>{markdown}</ReactMarkdown>
    </div>
  );
}
