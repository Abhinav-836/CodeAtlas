import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function Markdown({ source }) {
  const text = typeof source === "string" ? source : source?.summary || JSON.stringify(source, null, 2);
  return (
    <div className="prose-atlas">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}