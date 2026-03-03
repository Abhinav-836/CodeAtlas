export const API_URL = 'http://localhost:8000';

export const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  extracting: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
  scanning: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300',
  generating_report: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-300',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
};

export const SEVERITY_COLORS = {
  critical: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  info: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
};

export const MAX_FILE_SIZE_MB = 100;
export const SUPPORTED_FILE_TYPES = ['.zip'];
export const POLLING_INTERVAL = 2000; // 2 seconds
export const DEFAULT_EXPORT_FORMAT = 'json';