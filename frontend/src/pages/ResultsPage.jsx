import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Button from "../components/UI/Button";
import Card from "../components/UI/Card";
import ProgressBar from "../components/UI/ProgressBar";
import AnalysisChart from "../components/Charts/AnalysisChart";
import { useAnalysis } from "../hooks/useAnalysis";
import ReactMarkdown from "react-markdown";
import { SEVERITY_COLORS } from "../utils/constants";
import { reportsAPI } from "../utils/apiClient";

const MarkdownBlock = ({ source }) => {
  const text =
    typeof source === "string"
      ? source
      : source?.summary || JSON.stringify(source, null, 2);

  return (
    <ReactMarkdown
      components={{
        h1: (props) => <h1 className="text-2xl font-bold mt-4 mb-2" {...props} />,
        h2: (props) => <h2 className="text-xl font-semibold mt-3 mb-2" {...props} />,
        h3: (props) => <h3 className="text-lg font-medium mt-2 mb-1" {...props} />,
        p: (props) => <p className="text-gray-700 dark:text-gray-300 mb-3 leading-relaxed" {...props} />,
        ul: (props) => <ul className="list-disc pl-6 mb-3 space-y-1" {...props} />,
        ol: (props) => <ol className="list-decimal pl-6 mb-3 space-y-1" {...props} />,
        li: (props) => <li className="text-gray-700 dark:text-gray-300" {...props} />,
        strong: (props) => <strong className="font-semibold text-gray-900 dark:text-white" {...props} />,
        // Tables get a clean look. If the LLM ever sneaks one through,
        // it's readable rather than a wall of pipes.
        table: (props) => (
          <div className="overflow-x-auto my-4">
            <table className="min-w-full border-collapse border border-gray-200 dark:border-gray-700 text-sm" {...props} />
          </div>
        ),
        thead: (props) => <thead className="bg-gray-100 dark:bg-gray-800" {...props} />,
        th: (props) => (
          <th className="border border-gray-200 dark:border-gray-700 px-3 py-2 text-left font-semibold" {...props} />
        ),
        td: (props) => (
          <td className="border border-gray-200 dark:border-gray-700 px-3 py-2 align-top" {...props} />
        ),
        code: ({ inline, ...props }) =>
          inline ? (
            <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded text-sm" {...props} />
          ) : (
            <code className="block bg-gray-800 text-green-300 p-3 rounded-lg overflow-x-auto text-sm" {...props} />
          ),
      }}
    >
      {text}
    </ReactMarkdown>
  );
};

const ResultsPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("overview");
  const [aiExpanded, setAiExpanded] = useState(false);
  const { status, progress, results: result, error } = useAnalysis(taskId);

  const riskLevel = result?.overall_risk_level || result?.metrics?.risk || "none";
  const riskScore = result?.overall_risk_score ?? result?.metrics?.risk_score ?? 0;

  const getRiskColor = (level) =>
    ({
      critical: "bg-red-600", high: "bg-orange-500",
      medium: "bg-yellow-500", low: "bg-green-500", none: "bg-gray-500",
    }[level] || "bg-gray-500");

  const getSeverityBadge = (severity) =>
    SEVERITY_COLORS[severity] || SEVERITY_COLORS.info;

  const canDownload = Boolean(result?.report_id);

  const handleDownload = () => {
    if (!canDownload) return;
    window.open(reportsAPI.downloadReportUrl(result.report_id, "json"), "_blank", "noopener");
  };

  if (status !== "completed" || !result) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 py-12">
        <div className="container mx-auto px-4 max-w-2xl">
          <Card className="p-8 text-center bg-white/95 backdrop-blur">
            <div className="mb-6">
              <div className="w-24 h-24 mx-auto mb-4 relative">
                <div className="absolute inset-0 rounded-full bg-blue-500 animate-ping opacity-20" />
                <div className="absolute inset-2 rounded-full bg-gradient-to-r from-blue-600 to-purple-600 flex items-center justify-center">
                  <span className="text-4xl animate-pulse">🤖</span>
                </div>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">AI Analysis in Progress</h2>
              <p className="text-gray-600 dark:text-gray-400">Please wait while our AI analyzes your code</p>
            </div>
            <div className="mb-8">
              <div className="flex justify-between items-center mb-4">
                <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">Status:</span>
                <span className="px-4 py-2 bg-blue-100 dark:bg-blue-900 rounded-full text-blue-800 dark:text-blue-200 font-medium capitalize">
                  {status || "Starting..."}
                </span>
              </div>
              <div className="mt-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600 dark:text-gray-400">Progress</span>
                  <span className="font-bold text-blue-600 dark:text-blue-400">{progress}%</span>
                </div>
                <ProgressBar value={progress} max={100} className="h-4" />
              </div>
              <div className="mt-4 text-sm text-gray-500">
                Task ID: <span className="font-mono">{taskId}</span>
              </div>
            </div>
            {error && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg mb-4">
                <p className="text-red-600 dark:text-red-400">⚠️ {error}</p>
              </div>
            )}
            <Button variant="outline" onClick={() => navigate("/upload")} className="mt-4">
              Upload Another Repository
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  if (error) {
    const isTaskGone = typeof error === "string" && error.toLowerCase().includes("no longer available");
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 py-12">
        <div className="container mx-auto px-4 max-w-lg">
          <Card className="p-8 text-center bg-white/95 backdrop-blur">
            <div className="text-6xl mb-4">{isTaskGone ? "🔄" : "❌"}</div>
            <h2 className="text-2xl font-bold mb-2">
              {isTaskGone ? "Analysis Interrupted" : "Error Loading Results"}
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">{error}</p>
            <div className="flex justify-center gap-3">
              <Button onClick={() => navigate("/upload")} variant="primary">Start New Analysis</Button>
              {!isTaskGone && (
                <Button onClick={() => window.location.reload()} variant="outline">Retry</Button>
              )}
            </div>
          </Card>
        </div>
      </div>
    );
  }

  const aiInsights = result?.ai_insights;
  const complexity = result?.complexity;
  const perLang = complexity?.per_language || {};

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 py-8">
      <div className="container mx-auto px-4 max-w-7xl">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 mb-6">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center gap-4 mb-4 md:mb-0">
              <div className="w-16 h-16 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center">
                <span className="text-3xl">🤖</span>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">AI Analysis Results</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  Repository: {result?.repo_name || result?.path?.split("/").pop() || "Unknown"}
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className={`px-4 py-2 rounded-lg text-white text-center ${getRiskColor(riskLevel)}`}>
                <div className="text-xs opacity-90">Risk Level</div>
                <div className="font-bold text-lg">{String(riskLevel).toUpperCase()}</div>
              </div>
              <div className="bg-gray-800 dark:bg-gray-700 px-4 py-2 rounded-lg text-white text-center">
                <div className="text-xs opacity-90">Risk Score</div>
                <div className="font-bold text-lg">{riskScore}/100</div>
              </div>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-gray-600 dark:text-gray-400">Analysis Time:</span>
              <span className="font-bold">{result?.performance?.analysis_duration_seconds?.toFixed(2)}s</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-600 dark:text-gray-400">Files Analyzed:</span>
              <span className="font-bold">{result?.summary?.total_files}</span>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[
            { icon: "📁", color: "bg-blue-100 dark:bg-blue-900", numColor: "text-blue-600",
              value: result?.summary?.total_files || 0, label: "Total Files" },
            { icon: "📊", color: "bg-green-100 dark:bg-green-900", numColor: "text-green-600",
              value: (result?.metrics?.total_lines || 0).toLocaleString(), label: "Lines of Code" },
            { icon: "🌐", color: "bg-purple-100 dark:bg-purple-900", numColor: "text-purple-600",
              value: result?.languages?.language_count || 0, label: "Languages" },
            { icon: "🔒", color: "bg-orange-100 dark:bg-orange-900", numColor: "text-orange-600",
              value: result?.security?.vulnerabilities_found || 0, label: "Issues Found" },
          ].map((s) => (
            <Card key={s.label} className="p-4 hover:shadow-lg transition-shadow">
              <div className="flex items-center gap-3">
                <div className={`text-3xl ${s.color} w-12 h-12 rounded-lg flex items-center justify-center`}>
                  {s.icon}
                </div>
                <div>
                  <div className={`text-2xl font-bold ${s.numColor}`}>{s.value}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">{s.label}</div>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* AI Summary */}
        {aiInsights && (
          <Card className="p-6 mb-6 border-2 border-blue-400 dark:border-blue-600">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center">
                <span className="text-xl">🤖</span>
              </div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">AI Executive Summary</h2>
            </div>
            <div className={`prose dark:prose-invert max-w-none transition-all ${!aiExpanded ? "max-h-96 overflow-hidden relative" : ""}`}>
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 p-6 rounded-lg">
                <MarkdownBlock source={aiInsights} />
              </div>
              {!aiExpanded && (
                <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white dark:from-gray-800 to-transparent" />
              )}
            </div>
            <button
              onClick={() => setAiExpanded(!aiExpanded)}
              className="mt-4 text-blue-600 dark:text-blue-400 hover:underline font-medium flex items-center gap-1"
            >
              {aiExpanded ? "Show less" : "Read more"} <span>{aiExpanded ? "↑" : "↓"}</span>
            </button>
          </Card>
        )}

        {/* Tabs */}
        <div className="flex flex-wrap gap-2 mb-6 bg-white dark:bg-gray-800 p-2 rounded-xl shadow">
          {["overview", "security", "complexity", "languages", "ai"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg capitalize font-medium transition-colors ${
                activeTab === tab
                  ? "bg-gradient-to-r from-blue-600 to-purple-600 text-white"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
            >
              {tab === "overview" && "📋 "}
              {tab === "security" && "🔒 "}
              {tab === "complexity" && "📊 "}
              {tab === "languages" && "🌐 "}
              {tab === "ai" && "🤖 "}
              {tab}
            </button>
          ))}
        </div>

        <Card className="p-6 mb-6">
          {activeTab === "overview" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <span>📊</span> Key Metrics
                </h3>
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-3">
                  {[
                    ["Total Files", result?.summary?.total_files],
                    ["Total Lines", result?.metrics?.total_lines?.toLocaleString()],
                    ["Languages", result?.languages?.language_count],
                    ["Primary Language", result?.languages?.primary_language],
                    ["Risk Score", `${riskScore}/100`],
                  ].map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">{k}:</span>
                      <span className="font-bold">{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              {result?.recommendations?.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <span>💡</span> Recommendations
                  </h3>
                  <div className="space-y-3">
                    {result.recommendations.map((rec, index) => (
                      <div key={index} className={`p-4 rounded-lg border-l-4 ${
                        rec.priority === "critical" ? "border-l-red-600 bg-red-50 dark:bg-red-900/20"
                        : rec.priority === "high" ? "border-l-orange-500 bg-orange-50 dark:bg-orange-900/20"
                        : rec.priority === "medium" ? "border-l-yellow-500 bg-yellow-50 dark:bg-yellow-900/20"
                        : "border-l-blue-500 bg-blue-50 dark:bg-blue-900/20"
                      }`}>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs font-bold">{rec.priority?.toUpperCase()}</span>
                          <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">{rec.category}</span>
                        </div>
                        <h4 className="font-bold mb-1">{rec.title}</h4>
                        <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">{rec.description}</p>
                        <p className="text-sm text-blue-600 dark:text-blue-400">
                          <strong>Action:</strong> {rec.action}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "security" && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[["critical", "text-red-600", "border-l-red-600"],
                  ["high", "text-orange-500", "border-l-orange-500"],
                  ["medium", "text-yellow-500", "border-l-yellow-500"],
                  ["low", "text-blue-500", "border-l-blue-500"]].map(([level, textColor, borderColor]) => (
                  <div key={level} className={`text-center p-4 border-l-4 ${borderColor} bg-gray-50 dark:bg-gray-900 rounded`}>
                    <div className={`text-2xl font-bold ${textColor}`}>
                      {result?.security?.by_severity?.[level] || 0}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 capitalize">{level}</div>
                  </div>
                ))}
              </div>
              <AnalysisChart stats={{
                critical_issues: result?.security?.by_severity?.critical || 0,
                high_issues: result?.security?.by_severity?.high || 0,
                medium_issues: result?.security?.by_severity?.medium || 0,
                low_issues: result?.security?.by_severity?.low || 0,
              }} />
              {result?.security?.vulnerabilities?.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-4">🔍 Vulnerabilities</h3>
                  <div className="space-y-4">
                    {result.security.vulnerabilities.map((vuln, idx) => (
                      <div key={idx} className="border-l-4 border-l-red-500 pl-4 py-2">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-sm bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                              {vuln.file?.split("/").pop()}
                            </span>
                            <span className="text-sm text-gray-600 dark:text-gray-400">Line {vuln.line}</span>
                          </div>
                          <span className={`px-2 py-1 rounded text-xs font-bold ${getSeverityBadge(vuln.severity)}`}>
                            {vuln.severity?.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-sm font-medium mb-2">{vuln.pattern}</p>
                        <pre className="mt-2 p-3 bg-gray-900 text-green-300 text-xs rounded-lg overflow-x-auto">
                          {vuln.context}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "complexity" && (
            complexity && Object.keys(perLang).length > 0 ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[["total_functions", "Functions", "text-purple-600"],
                    ["total_classes", "Classes", "text-indigo-600"],
                    ["avg_complexity_score", "Avg Complexity", "text-pink-600"],
                    ["total_lines", "Lines", "text-teal-600"]].map(([field, label, color]) => {
                    const raw = complexity[field];
                    const display = typeof raw === "number" && field === "avg_complexity_score"
                      ? raw.toFixed(2) : raw ?? 0;
                    return (
                      <div key={field} className="text-center p-4 bg-gray-50 dark:bg-gray-900 rounded">
                        <div className={`text-2xl font-bold ${color}`}>{display}</div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">{label}</div>
                      </div>
                    );
                  })}
                </div>

                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                  <span>Confidence:</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    complexity.confidence === "ast" ? "bg-green-100 text-green-800"
                    : complexity.confidence === "parser" ? "bg-blue-100 text-blue-800"
                    : complexity.confidence === "heuristic" ? "bg-yellow-100 text-yellow-800"
                    : "bg-gray-100 text-gray-800"
                  }`}>
                    {complexity.confidence === "ast" ? "AST — exact"
                      : complexity.confidence === "parser" ? "Parser — exact"
                      : complexity.confidence === "heuristic" ? "Heuristic — approximate"
                      : "File stats only"}
                  </span>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-4">🌐 Per-Language Breakdown</h3>
                  <div className="space-y-3">
                    {Object.entries(perLang).map(([lang, data]) => (
                      <div key={lang} className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                        <div className="flex justify-between items-center mb-2">
                          <span className="font-bold">{lang}</span>
                          <span className="text-xs text-gray-500">
                            {data.files} files · avg cx {data.avg_complexity_score}
                          </span>
                        </div>
                        <div className="flex gap-4 text-xs text-gray-600 dark:text-gray-400">
                          <span>{data.total_functions} functions</span>
                          <span>{data.total_classes} classes</span>
                          <span>{data.total_lines} lines</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {complexity.most_complex_files?.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold mb-4">📈 Most Complex Files</h3>
                    <div className="space-y-3">
                      {complexity.most_complex_files.slice(0, 10).map((file, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate max-w-md">{file.file?.split("/").pop()}</div>
                            <div className="flex gap-3 text-xs text-gray-600 dark:text-gray-400 mt-1 flex-wrap">
                              {file.language && <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded">{file.language}</span>}
                              <span>Functions: {file.functions}</span>
                              <span>Classes: {file.classes}</span>
                              <span>Lines: {file.lines}</span>
                            </div>
                          </div>
                          <div className="ml-4 px-3 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-300 rounded-full text-sm font-bold">
                            {file.complexity_score}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="text-4xl mb-3">📊</div>
                <h3 className="text-lg font-semibold mb-2">No complexity data available</h3>
                <p className="text-gray-600 dark:text-gray-400">
                  This repository doesn&apos;t contain any supported source files.
                </p>
              </div>
            )
          )}

          {activeTab === "languages" && result?.languages?.detected_languages && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold mb-4">🌐 Language Distribution</h3>
              {Object.entries(result.languages.detected_languages).map(([lang, data]) => (
                <div key={lang} className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-bold">{lang}</span>
                    <span className="text-sm text-gray-600 dark:text-gray-400">{data.count} files</span>
                  </div>
                  <ProgressBar value={data.percentage} max={100} />
                  <p className="text-right text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {data.percentage}% of codebase
                  </p>
                </div>
              ))}
            </div>
          )}

          {activeTab === "ai" && (
            <div>
              <h3 className="text-lg font-semibold mb-4">🤖 Detailed AI Analysis</h3>
              {aiInsights ? (
                <div className="prose dark:prose-invert max-w-none">
                  <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 p-6 rounded-lg">
                    <MarkdownBlock source={aiInsights} />
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <p className="text-gray-600 dark:text-gray-400">AI insights not available</p>
                </div>
              )}
            </div>
          )}
        </Card>

        <div className="flex flex-wrap justify-center gap-4 mt-8">
          <Button onClick={handleDownload} disabled={!canDownload} variant="primary"
            className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700">
            <span className="flex items-center gap-2">
              <span>⬇️</span><span>{canDownload ? "Download JSON" : "Download unavailable"}</span>
            </span>
          </Button>
          <Button onClick={() => navigate("/upload")} variant="outline">
            <span className="flex items-center gap-2"><span>📤</span><span>New Analysis</span></span>
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ResultsPage;