import { useNavigate } from "react-router-dom";
import Button from "../components/UI/Button";
import Card from "../components/UI/Card";

/* ======================
   FEATURES DATA
====================== */
const FEATURES = [
  {
    icon: "📦",
    title: "Upload & Analyze",
    description: "Upload ZIP files or GitHub repositories for comprehensive code analysis",
  },
  {
    icon: "🔍",
    title: "Deep Scanning",
    description: "Detect security vulnerabilities, code smells, and performance issues",
  },
  {
    icon: "📊",
    title: "Detailed Reports",
    description: "Get actionable insights with visual charts and recommendations",
  },
  {
    icon: "⚡",
    title: "Fast Processing",
    description: "AI-powered analysis that delivers results in minutes",
  },
];

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <main className="min-h-screen">
      {/* ======================
         HERO SECTION
      ====================== */}
      <section className="bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 py-20">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-5xl md:text-6xl font-bold mb-6">
            Code<span className="text-blue-600 dark:text-blue-400">Atlas</span>
          </h1>

          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-3xl mx-auto">
            AI-powered code intelligence platform. Analyze, optimize, and secure
            your codebase with comprehensive insights.
          </p>

          <div className="flex justify-center gap-4">
            <Button
              size="lg"
              onClick={() => navigate("/upload")}
              aria-label="Upload repository for analysis"
              className="px-8"
            >
              🚀 Get Started
            </Button>

            <Button
              variant="outline"
              size="lg"
              onClick={() => navigate("/reports")}
              aria-label="View analysis reports"
            >
              📊 View Reports
            </Button>
          </div>
        </div>
      </section>

      {/* ======================
         FEATURES SECTION
      ====================== */}
      <section className="container mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">
          Why Choose CodeAtlas?
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {FEATURES.map((feature, index) => (
            <Card
              key={index}
              className="text-center p-6 hover:shadow-lg transition-shadow"
            >
              <div className="text-4xl mb-4">{feature.icon}</div>
              <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
              <p className="text-gray-600 dark:text-gray-400">
                {feature.description}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* ======================
         HOW IT WORKS
      ====================== */}
      <section className="bg-gray-50 dark:bg-gray-900 py-16">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            How It Works
          </h2>

          <div className="relative max-w-5xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
              {[
                { step: "1", title: "Upload", desc: "Upload your code repository" },
                { step: "2", title: "Analyze", desc: "AI scans for issues" },
                { step: "3", title: "Review", desc: "Get detailed insights" },
                { step: "4", title: "Improve", desc: "Implement recommendations" },
              ].map((item) => (
                <div key={item.step} className="text-center">
                  <div className="mx-auto w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center mb-4">
                    <span className="text-2xl font-bold text-blue-600 dark:text-blue-300">
                      {item.step}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold mb-2">{item.title}</h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    {item.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ======================
         CTA SECTION
      ====================== */}
      <section className="container mx-auto px-4 py-16 text-center">
        <h2 className="text-3xl font-bold mb-6">
          Ready to Improve Your Code?
        </h2>

        <p className="text-xl text-gray-600 dark:text-gray-300 mb-8">
          Join thousands of developers who trust CodeAtlas for their code analysis.
        </p>

        <Button
          size="lg"
          onClick={() => navigate("/upload")}
          className="px-12 text-lg"
          aria-label="Start free code analysis"
        >
          Start Free Analysis
        </Button>
      </section>
    </main>
  );
}
