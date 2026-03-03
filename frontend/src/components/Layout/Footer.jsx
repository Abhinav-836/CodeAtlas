export default function Footer() {
    return (
      <footer className="bg-white dark:bg-gray-800 border-t dark:border-gray-700 mt-16">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <div className="flex items-center space-x-2">
                <div className="w-6 h-6 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">C</span>
                </div>
                <span className="text-lg font-bold text-gray-900 dark:text-white">
                  Code<span className="text-blue-600">Atlas</span>
                </span>
              </div>
              <p className="text-gray-600 dark:text-gray-400 text-sm mt-2">
                AI-powered code intelligence platform
              </p>
            </div>
            
            <div className="flex space-x-6">
              <a href="#" className="text-gray-600 dark:text-gray-400 hover:text-blue-600">
                GitHub
              </a>
              <a href="#" className="text-gray-600 dark:text-gray-400 hover:text-blue-600">
                Documentation
              </a>
              <a href="#" className="text-gray-600 dark:text-gray-400 hover:text-blue-600">
                Contact
              </a>
            </div>
          </div>
          
          <div className="border-t dark:border-gray-700 mt-6 pt-6 text-center text-gray-500 dark:text-gray-400 text-sm">
            <p>© {new Date().getFullYear()} CodeAtlas. All rights reserved.</p>
            <p className="mt-1">Built with ❤️ for developers</p>
          </div>
        </div>
      </footer>
    );
  }