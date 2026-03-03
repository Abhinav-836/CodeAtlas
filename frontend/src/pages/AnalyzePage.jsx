import { useState, useEffect } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useAnalysis } from "../hooks/useAnalysis";
import { useToast } from "../hooks/useToast";
import Button from "../components/UI/Button";
import Card from "../components/UI/Card";
import ProgressBar from "../components/UI/ProgressBar";
import { analyzeAPI } from "../utils/apiClient";

export default function AnalyzePage() {
  const { taskId: routeTaskId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { showToast } = useToast();

  const [path, setPath] = useState(location.state?.repositoryPath || "");
  const [taskId, setTaskId] = useState(routeTaskId || null);
  const [startError, setStartError] = useState(null);
  const [aiStatusMessage, setAiStatusMessage] = useState("");

  const { status, progress, results, error } = useAnalysis(taskId);

  // AI-powered status messages based on progress
  useEffect(() => {
    if (status === 'queued') {
      setAiStatusMessage("🤖 AI is preparing to analyze your code...");
    } else if (status === 'extracting') {
      setAiStatusMessage("📦 Extracting and preparing files for AI analysis...");
    } else if (status === 'scanning') {
      setAiStatusMessage("🔍 AI is scanning for security vulnerabilities and secrets...");
    } else if (status === 'analyzing') {
      setAiStatusMessage("🧠 AI is analyzing code complexity and structure...");
    } else if (status === 'generating_report') {
      setAiStatusMessage("📝 AI is generating comprehensive insights and recommendations...");
    } else if (status === 'completed') {
      setAiStatusMessage("✅ AI analysis complete! Redirecting to results...");
    } else if (status === 'running') {
      setAiStatusMessage("⚙️ AI is processing your codebase...");
    }
  }, [status]);

  // Auto-navigate to results when analysis is complete
  useEffect(() => {
    if (results) {
      showToast("AI analysis completed successfully!", "success");
      navigate(`/results/${taskId}`);
    }
  }, [results, taskId, navigate, showToast]);

  const handleStartAnalysis = async () => {
    if (!path.trim()) {
      setStartError("Please enter a repository path");
      return;
    }

    try {
      setStartError(null);
      showToast("Starting AI analysis...", "info");
      
      // Call the API to start analysis
      const response = await fetch(`http://localhost:8000/api/analyze?path=${encodeURIComponent(path)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to start analysis');
      }
      
      console.log("AI Analysis started:", data);
      showToast("AI analysis started successfully!", "success");
      
      // Set the task ID - this will trigger the progress screen
      setTaskId(data.task_id);
      
    } catch (err) {
      console.error("Start analysis error:", err);
      setStartError(err.message);
      showToast(err.message, "error");
    }
  };

  const resetAnalysis = () => {
    setTaskId(null);
    setPath("");
    setStartError(null);
    navigate("/analyze");
  };

  // If we have a taskId, show AI-powered progress
  if (taskId) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 py-12">
        <div className="container mx-auto px-4 max-w-2xl">
          <Card className="p-8 text-center bg-white/95 backdrop-blur">
            <div className="mb-6">
              <div className="w-24 h-24 mx-auto mb-4 relative">
                <div className="absolute inset-0 rounded-full bg-blue-500 animate-ping opacity-20"></div>
                <div className="absolute inset-2 rounded-full bg-gradient-to-r from-blue-600 to-purple-600 flex items-center justify-center">
                  <span className="text-4xl animate-pulse">🤖</span>
                </div>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                AI Analysis in Progress
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Please wait while our AI analyzes your code
              </p>
            </div>
            
            <div className="mb-8">
              <div className="flex justify-between items-center mb-4">
                <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">Status:</span>
                <span className="px-4 py-2 bg-blue-100 dark:bg-blue-900 rounded-full text-blue-800 dark:text-blue-200 font-medium capitalize">
                  {status || "Starting..."}
                </span>
              </div>
              
              {/* Progress Bar */}
              <div className="mt-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600 dark:text-gray-400">Analysis Progress</span>
                  <span className="font-bold text-blue-600 dark:text-blue-400">{progress}%</span>
                </div>
                <ProgressBar value={progress} max={100} className="h-4" />
              </div>

              {/* AI Status Message with Animation */}
              <div className="mt-6 p-6 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <div className="flex items-center justify-center space-x-3 mb-3">
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
                  <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-pink-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
                <p className="text-gray-700 dark:text-gray-300 font-medium">
                  {aiStatusMessage}
                </p>
              </div>

              {/* Task ID */}
              <div className="mt-4 text-sm text-gray-500">
                Task ID: <span className="font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">{taskId}</span>
              </div>

              {/* Progress Steps */}
              <div className="mt-8 grid grid-cols-5 gap-1 text-xs">
                {['Queued', 'Extract', 'Scan', 'Analyze', 'Report'].map((step, index) => {
                  const stepProgress = (index + 1) * 20;
                  const isComplete = progress >= stepProgress;
                  const isActive = progress >= stepProgress - 20 && progress < stepProgress;
                  
                  return (
                    <div key={step} className="text-center">
                      <div className={`h-1 mb-2 rounded-full transition-all ${
                        isComplete ? 'bg-green-500' : 
                        isActive ? 'bg-blue-500 animate-pulse' : 
                        'bg-gray-300 dark:bg-gray-700'
                      }`}></div>
                      <span className={`${
                        isComplete ? 'text-green-600 dark:text-green-400' :
                        isActive ? 'text-blue-600 dark:text-blue-400 font-bold' :
                        'text-gray-500 dark:text-gray-500'
                      }`}>
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

            <Button variant="outline" onClick={resetAnalysis} className="mt-4">
              Cancel Analysis
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  // Initial input screen (no taskId)
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-purple-700 py-12">
      <div className="container mx-auto px-4 max-w-2xl">
        <h1 className="text-3xl font-bold text-white mb-6 text-center">AI-Powered Code Analysis</h1>
        
        <Card className="p-8 bg-white/95 backdrop-blur">
          <div className="text-center mb-6">
            <div className="text-6xl mb-4 animate-pulse">🤖</div>
            <h2 className="text-xl text-gray-600 dark:text-gray-400">
              Enter your repository path to start AI analysis
            </h2>
          </div>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                Repository Path
              </label>
              <input
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="C:\Users\name\repo or /home/user/repo"
                className="w-full px-4 py-3 border rounded-lg dark:bg-gray-800 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {location.state?.repositoryPath && (
                <p className="mt-2 text-sm text-green-600">
                  ✅ Path loaded from uploaded file
                </p>
              )}
            </div>

            <Button
              onClick={handleStartAnalysis}
              disabled={!path.trim()}
              className="w-full py-3 text-lg bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              size="lg"
            >
              <span className="flex items-center justify-center gap-2">
                <span>🤖</span>
                <span>Start AI Analysis</span>
              </span>
            </Button>

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
                <li>📄 • Automatic README generation</li>
              </ul>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}