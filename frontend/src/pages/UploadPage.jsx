import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/UI/Button";
import Card from "../components/UI/Card";
import { uploadAPI, analyzeAPI } from "../utils/apiClient";
import { useToast } from "../hooks/useToast";

export default function UploadPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [file, setFile] = useState(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [uploadType, setUploadType] = useState("zip");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const handleUpload = async () => {
    setError("");
    setLoading(true);

    try {
      let uploadResponse;
      let extractedPath;

      if (uploadType === "zip") {
        if (!file) {
          setError("Please select a ZIP file");
          setLoading(false);
          return;
        }
        const formData = new FormData();
        formData.append("file", file);
        uploadResponse = await uploadAPI.uploadZip(formData);
        extractedPath = uploadResponse.data.extracted_to;
      } else {
        if (!githubUrl.trim()) {
          setError("Please enter a GitHub URL");
          setLoading(false);
          return;
        }
        
        console.log("Uploading GitHub URL:", githubUrl);
        
        // FIXED: Send the URL directly - backend handles all formats
        uploadResponse = await uploadAPI.uploadGithub(githubUrl, "main");
        
        extractedPath = uploadResponse.data.local_path;
        console.log("GitHub upload response:", uploadResponse.data);
      }

      console.log("Upload successful, path:", extractedPath);
      showToast("Upload successful! Starting analysis...", "success");
      
      const analysisResponse = await analyzeAPI.startAnalysis(extractedPath);
      const taskId = analysisResponse.data.task_id;
      
      console.log("Analysis started with task ID:", taskId);
      showToast("Analysis started successfully!", "success");
      
      navigate(`/results/${taskId}`);

    } catch (err) {
      console.error("Upload error:", err);
      
      // Better error message
      let errorMessage = "Upload failed";
      if (err?.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      showToast(errorMessage, "error");
    } finally {
      setLoading(false);
    }
  };

  // Drag and drop handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800 py-12">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-pink-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute top-40 left-40 w-80 h-80 bg-indigo-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      <div className="container mx-auto px-4 relative z-10">
        {/* Header Section with Stats */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center p-2 bg-white/10 backdrop-blur-lg rounded-full mb-6">
            <span className="px-4 py-2 text-sm font-medium text-white">
              🚀 AI-Powered Code Analysis
            </span>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-4">
            Upload Your{' '}
            <span className="bg-gradient-to-r from-yellow-400 to-pink-400 text-transparent bg-clip-text">
              Repository
            </span>
          </h1>
          
          <p className="text-xl text-white/80 max-w-2xl mx-auto">
            Get instant AI-powered insights about your code's security, complexity, and architecture
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto mb-12">
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 text-center transform hover:scale-105 transition-transform">
            <div className="text-4xl mb-3">🔍</div>
            <div className="text-2xl font-bold text-white">100+</div>
            <div className="text-white/70">Security Patterns</div>
          </div>
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 text-center transform hover:scale-105 transition-transform">
            <div className="text-4xl mb-3">⚡</div>
            <div className="text-2xl font-bold text-white">30s</div>
            <div className="text-white/70">Average Analysis</div>
          </div>
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 text-center transform hover:scale-105 transition-transform">
            <div className="text-4xl mb-3">📊</div>
            <div className="text-2xl font-bold text-white">10+</div>
            <div className="text-white/70">Languages Supported</div>
          </div>
        </div>

        {/* Main Upload Card */}
        <Card className="max-w-2xl mx-auto bg-white/95 backdrop-blur-xl border-0 shadow-2xl">
          <div className="p-8">
            {/* Toggle Buttons */}
            <div className="flex gap-3 mb-8 p-1.5 bg-gray-100 dark:bg-gray-800 rounded-2xl">
              <button
                onClick={() => setUploadType("zip")}
                className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all ${
                  uploadType === "zip"
                    ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/30"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                }`}
              >
                <span className="flex items-center justify-center gap-2">
                  <span className="text-xl">📦</span>
                  <span>ZIP File</span>
                </span>
              </button>
              <button
                onClick={() => setUploadType("github")}
                className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all ${
                  uploadType === "github"
                    ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/30"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                }`}
              >
                <span className="flex items-center justify-center gap-2">
                  <span className="text-xl">🐙</span>
                  <span>GitHub</span>
                </span>
              </button>
            </div>

            {/* Upload Area */}
            {uploadType === "zip" ? (
              <div
                className={`relative border-3 border-dashed rounded-2xl p-10 transition-all ${
                  dragActive
                    ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 scale-102"
                    : "border-gray-300 dark:border-gray-600 hover:border-indigo-400 dark:hover:border-indigo-500"
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  accept=".zip"
                  onChange={(e) => setFile(e.target.files[0])}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  id="file-upload"
                />
                
                <div className="text-center">
                  <div className="text-7xl mb-4 animate-bounce">
                    {file ? "📄" : "📦"}
                  </div>
                  
                  {file ? (
                    <div className="space-y-3">
                      <p className="text-xl font-semibold text-indigo-600 dark:text-indigo-400">
                        {file.name}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                      <button
                        onClick={() => setFile(null)}
                        className="text-sm text-red-500 hover:text-red-700 font-medium"
                      >
                        Remove file
                      </button>
                    </div>
                  ) : (
                    <>
                      <p className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
                        Drag & drop your ZIP file here
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                        or click to browse
                      </p>
                      <div className="inline-flex items-center gap-2 text-xs text-gray-400">
                        <span>Max size: 100MB</span>
                        <span className="w-1 h-1 bg-gray-400 rounded-full"></span>
                        <span>ZIP only</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <span className="text-2xl text-gray-400">🔗</span>
                  </div>
                  <input
                    type="url"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/username/repository"
                    className={`w-full pl-12 pr-4 py-4 border-2 rounded-2xl dark:bg-gray-800 focus:ring-4 transition-all ${
                      error && uploadType === "github"
                        ? "border-red-500 focus:border-red-500 focus:ring-red-200 dark:focus:ring-red-900/30"
                        : "border-gray-200 dark:border-gray-700 focus:border-indigo-500 dark:focus:border-indigo-400 focus:ring-indigo-200 dark:focus:ring-indigo-900/30"
                    }`}
                  />
                </div>
                
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Any GitHub URL format works!</span>
                </div>
                
                {/* Example URLs */}
                <div className="text-xs text-gray-400 space-y-1">
                  <p className="font-medium text-gray-500 dark:text-gray-400">Examples that work:</p>
                  <p className="font-mono">https://github.com/username/repo</p>
                  <p className="font-mono">https://github.com/username/repo.git</p>
                  <p className="font-mono">git@github.com:username/repo.git</p>
                  <p className="font-mono">username/repo</p>
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="mt-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl animate-shake">
                <p className="text-red-600 dark:text-red-400 flex items-center gap-2">
                  <span>⚠️</span>
                  {error}
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="mt-8 space-y-3">
              <Button
                onClick={handleUpload}
                loading={loading}
                disabled={loading || (uploadType === "zip" ? !file : !githubUrl)}
                className="w-full py-4 text-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-xl shadow-lg shadow-indigo-500/30 transform hover:scale-105 transition-all"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-3">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>Processing...</span>
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-3">
                    <span>🚀</span>
                    <span>{uploadType === "zip" ? "Upload & Analyze" : "Analyze Repository"}</span>
                  </span>
                )}
              </Button>

              <p className="text-center text-sm text-gray-500 dark:text-gray-400">
                By uploading, you agree to our{' '}
                <a href="#" className="text-indigo-600 dark:text-indigo-400 hover:underline">
                  Terms of Service
                </a>
              </p>
            </div>
          </div>
        </Card>

        {/* Features Preview */}
        <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto">
          <div className="text-center">
            <div className="text-3xl mb-2">🔒</div>
            <div className="text-sm font-medium text-white">Security Scan</div>
          </div>
          <div className="text-center">
            <div className="text-3xl mb-2">📈</div>
            <div className="text-sm font-medium text-white">Complexity Analysis</div>
          </div>
          <div className="text-center">
            <div className="text-3xl mb-2">🤖</div>
            <div className="text-sm font-medium text-white">AI Insights</div>
          </div>
          <div className="text-center">
            <div className="text-3xl mb-2">📊</div>
            <div className="text-sm font-medium text-white">Detailed Reports</div>
          </div>
        </div>
      </div>

      {/* Add custom animations */}
      <style jsx>{`
        @keyframes blob {
          0% { transform: translate(0px, 0px) scale(1); }
          33% { transform: translate(30px, -50px) scale(1.1); }
          66% { transform: translate(-20px, 20px) scale(0.9); }
          100% { transform: translate(0px, 0px) scale(1); }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
          20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }
        .scale-102 {
          transform: scale(1.02);
        }
      `}</style>
    </div>
  );
}