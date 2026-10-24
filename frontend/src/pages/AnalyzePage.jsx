import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAnalysis } from "../hooks/useAnalysis";
import { useToast } from "../hooks/useToast";
import Button from "../components/UI/Button";
import Card from "../components/UI/Card";
import ProgressBar from "../components/UI/ProgressBar";
import { analyzeAPI } from "../utils/apiClient";

const STATUS_MESSAGES = {
  queued: "🤖 AI is preparing to analyze your code...",
  extracting: "📦 Extracting and preparing files for AI analysis...",
  scanning: "🔍 AI is scanning for security vulnerabilities and secrets...",
  analyzing: "🧠 AI is analyzing code complexity and structure...",
  generating_report: "📝 AI is generating comprehensive insights and recommendations...",
  running: "⚙️ AI is processing your codebase...",
  completed: "✅ AI analysis complete! Redirecting to results...",
  failed: "❌ The analysis could not be completed.",
  timeout: "⏱️ The analysis took too long and was stopped.",
  cancelled: "🛑 The analysis was cancelled.",
};

const STEPS = ["Queued", "Extract", "Scan", "Analyze", "Report"];

export default function AnalyzePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { showToast } = useToast();

  const uploadedPath = location.state?.repositoryPath || "";
  const [path, setPath] = useState(uploadedPath);
  const [taskId, setTaskId] = useState(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState(null);

  const { status, progress, results, error } = useAnalysis(taskId);
  const aiStatusMessage = STATUS_MESSAGES[status] || "";

  // Auto-navigate to results when analysis is complete
  useEffect(() => {
    if (results) {
      showToast("AI analysis completed successfully!", "success");
      navigate(`/results/${taskId}`);
    }
  }, [results, taskId, navigate, showToast]);

  // Surface failures as a toast as well as inline.
  useEffect(() => {
    if (error) showToast(error, "error", 5000);
  }, [error, showToast]);

  const handleStartAnalysis = async () => {
    if (!path.trim()) {
      setStartError("Please enter a repository path");
      return;
    }
    // Prevent double-clicks starting two analyses.
    if (starting) return;
    setStarting(true);

    try {
      setStartError(null);
      // Goes through apiClient, which respects VITE_API_URL.
      const { data } = await analyzeAPI.startAnalysis(path.trim());
      showToast("AI analysis started", "success");
      setTaskId(data.task_id);
    } catch (err) {
      console.error("Start analysis error:", err);
      const message =
        err?.response?.data?.detail ||
        (err?.code === "ERR_NETWORK"
          ? "Cannot reach the CodeAtlas server. It may be waking up - please retry in a minute."
          : err?.message) ||
        "Failed to start analysis";
      setStartError(message);
      showToast(message, "error");
    } finally {
      setStarting(false);
    }
  };

  const resetAnalysis = () => {
    setTaskId(null);
    setStartError(null);
    // Keep the uploaded path so "Try again" doesn't force a re-upload.
    setPath(uploadedPath);
  };

  // ── Progress screen ───────────────────────────────────────────
  if (taskId) {
    const finished = Boolean(error);

    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 py-12">
        <div className="container mx-auto px-4 max-w-2xl">
          <Card className="p-8 text-center bg-white/95 backdrop-blur">
            <div className="mb-6">
              <div className="w-24 h-24 mx-auto mb-4 relative">
                {!finished && (
                  <div className="absolute inset-0 rounded-full bg-blue-500 animate-ping opacity-20"></div>
                )}
                <div className="absolute inset-2 rounded-full bg-gradient-to-r from-blue-600 to-purple-600 flex items-center justify-center">
                  <span className={`text-4xl ${finished ? "" : "animate-pulse"}`}>{finished ? "⚠️" : "🤖"}</span>
                </div>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {finished ? "Analysis Stopped" : "AI Analysis in Progress"}
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                {finished
                  ? "Something went wrong - details below."
                  : "Please wait while our AI analyzes your code"}
              </p>
            </div>

            <div className="mb-8">
              <div className="flex justify-between items-center mb-4">
                <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">Status:</span>
                <span className="px-4 py-2 bg-blue-100 dark:bg-blue-900 rounded-full text-blue-800 dark:text-blue-200 font-medium capitalize">
                  {status ? status.replace(/_/g, " ") : "Starting..."}
                </span>
              </div>

              <div className="mt-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600 dark:text-gray-400">Analysis Progress</span>
                  <span className="font-bold text-blue-600 dark:text-blue-400">{progress}%</span>
                </div>
                <ProgressBar value={progress} max={100} className="h-4" />
              </div>

              {aiStatusMessage && (
                <div className="mt-6 p-6 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  {!finished && (
                    <div className="flex items-center justify-center space-x-3 mb-3">
                      <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: "0s" }}></div>
                      <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                      <div className="w-2 h-2 bg-pink-600 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></div>
                    </div>
                  )}
                  <p className="text-gray-700 dark:text-gray-300 font-medium">{aiStatusMessage}</p>
                </div>
              )}

              <div className="mt-4 text-sm text-gray-500 break-all">
                Task ID:{" "}
                <span className="font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">{taskId}</span>
              </div>

              <div className="mt-8 grid grid-cols-5 gap-1 text-xs">
                {STEPS.map((step, index) => {
                  const stepProgress = (index + 1) * 20;
                  const isComplete = progress >= stepProgress;
                  const isActive = !finished && progress >= stepProgress - 20 && progress < stepProgress;

                  return (
                    <div key={step} className="text-center">
                      <div
                        className={`h-1 mb-2 rounded-full transition-all ${
                          isComplete
                            ? "bg-green-500"
                            : isActive
                            ? "bg-blue-500 animate-pulse"
                            : "bg-gray-300 dark:bg-gray-700"
                        }`}
                      ></div>
                      <span
                        className={
                          isComplete
                            ? "text-green-600 dark:text-green-400"
                            : isActive
                            ? "text-blue-600 dark:text-blue-400 font-bold"
                            : "text-gray-500 dark:text-gray-500"
                        }
                      >
                        {step}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {error && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg mb-4">
                <p className="text-red-600 dark:text-red-400">⚠️ {error}</p>
              </div>
            )}

            <div className="flex flex-wrap justify-center gap-3 mt-4">
              <Button variant="outline" onClick={resetAnalysis}>
                {finished ? "Try Again" : "Cancel Analysis"}
              </Button>
              {finished && (
                <Button onClick={() => navigate("/upload")}>Upload Another Repository</Button>
              )}
            </div>
          </Card>
        </div>
      </div>
    );
  }

  // ── Start screen ──────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 py-12">
      <div className="container mx-auto px-4 max-w-2xl">
        <h1 className="text-3xl font-bold text-white mb-6 text-center">AI-Powered Code Analysis</h1>

        <Card className="p-8 bg-white/95 backdrop-blur">
          <div className="text-center mb-6">
            <div className="text-6xl mb-4 animate-pulse">🤖</div>
            <h2 className="text-xl text-gray-600 dark:text-gray-400">
              {uploadedPath
                ? "Your repository is ready - start the analysis"
                : "Upload a repository first, then start the analysis here"}
            </h2>
          </div>

          <div className="space-y-6">
            <div>
              <label htmlFor="repo-path" className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                Repository Path
              </label>
              <input
                id="repo-path"
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="Upload a ZIP or GitHub repo first - the path is filled in for you"
                className="w-full px-4 py-3 border rounded-lg dark:bg-gray-800 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {uploadedPath && (
                <p className="mt-2 text-sm text-green-600">✅ Path loaded from your upload</p>
              )}
            </div>

            <Button
              onClick={handleStartAnalysis}
              disabled={!path.trim()}
              loading={starting}
              className="w-full py-3 text-lg bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              size="lg"
            >
              <span className="flex items-center justify-center gap-2">
                <span>🤖</span>
                <span>Start AI Analysis</span>
              </span>
            </Button>

            {!uploadedPath && (
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
                Nothing uploaded yet?{" "}
                <button
                  type="button"
                  onClick={() => navigate("/upload")}
                  className="text-blue-600 hover:underline"
                >
                  Upload a repository
                </button>
              </p>
            )}

            {startError && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-red-600 dark:text-red-400">⚠️ {startError}</p>
              </div>
            )}

            <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <h3 className="font-semibold mb-2 text-blue-800 dark:text-blue-300">What our AI analyzes:</h3>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <li>🔍 • Security vulnerabilities and hardcoded secrets</li>
                <li>📊 • Code complexity and maintainability</li>
                <li>🏗️ • Architecture patterns and dependencies</li>
                <li>🌐 • Programming languages and frameworks</li>
                <li>💡 • Actionable recommendations for improvement</li>
              </ul>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}