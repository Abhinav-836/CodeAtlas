import { useEffect, useRef } from "react";
import Card from "../UI/Card";

export default function AnalysisChart({ stats }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !stats) return;

    const dpr = window.devicePixelRatio || 1;
    const cssWidth = 300;
    const cssHeight = 300;
    canvas.width = cssWidth * dpr;
    canvas.height = cssHeight * dpr;
    canvas.style.width = `${cssWidth}px`;
    canvas.style.height = `${cssHeight}px`;

    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssWidth, cssHeight);

    const issuesData = [
      { label: "Critical", value: stats.critical_issues || 0, color: "#ef4444" },
      { label: "High", value: stats.high_issues || 0, color: "#f97316" },
      { label: "Medium", value: stats.medium_issues || 0, color: "#eab308" },
      { label: "Low", value: stats.low_issues || 0, color: "#3b82f6" },
    ].filter((i) => i.value > 0);

    if (issuesData.length === 0) {
      ctx.font = "14px Arial";
      ctx.fillStyle = "#6b7280";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("No issues found", cssWidth / 2, cssHeight / 2);
      return;
    }

    const total = issuesData.reduce((s, i) => s + i.value, 0);
    const cx = cssWidth / 2;
    const cy = cssHeight / 2;
    const radius = Math.min(cx, cy) - 40;

    let start = 0;
    issuesData.forEach((item) => {
      const slice = (item.value / total) * 2 * Math.PI;

      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius, start, start + slice);
      ctx.closePath();
      ctx.fillStyle = item.color;
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.stroke();

      const mid = start + slice / 2;
      const lx = cx + Math.cos(mid) * radius * 0.7;
      const ly = cy + Math.sin(mid) * radius * 0.7;
      const pct = Math.round((item.value / total) * 100);

      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 14px Arial";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(`${pct}%`, lx, ly);

      start += slice;
    });

    ctx.beginPath();
    ctx.arc(cx, cy, radius * 0.4, 0, 2 * Math.PI);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = "#e5e7eb";
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = "#111827";
    ctx.font = "bold 20px Arial";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(total), cx, cy);
  }, [stats]);

  const legendItems = stats
    ? [
        { label: "Critical", value: stats.critical_issues || 0, color: "#ef4444" },
        { label: "High", value: stats.high_issues || 0, color: "#f97316" },
        { label: "Medium", value: stats.medium_issues || 0, color: "#eab308" },
        { label: "Low", value: stats.low_issues || 0, color: "#3b82f6" },
      ].filter((i) => i.value > 0)
    : [];

  const total = legendItems.reduce((s, i) => s + i.value, 0);

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4 text-gray-700 dark:text-gray-300">
        Issues Distribution
      </h3>

      <div className="flex flex-col md:flex-row items-center gap-8">
        <canvas ref={canvasRef} className="max-w-full h-auto" />

        <div className="flex-1 space-y-3">
          {legendItems.map((item) => {
            const pct = total > 0 ? Math.round((item.value / total) * 100) : 0;
            return (
              <div
                key={item.label}
                className="flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {item.label}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {item.value} issues
                  </span>
                  <span className="text-sm font-bold w-12 text-right">
                    {pct}%
                  </span>
                </div>
              </div>
            );
          })}
          {legendItems.length === 0 && (
            <p className="text-center text-gray-500 dark:text-gray-400 py-4">
              No issues to display
            </p>
          )}
        </div>
      </div>
    </Card>
  );
}