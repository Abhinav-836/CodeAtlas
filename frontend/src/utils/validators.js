export const isValidGitHubUrl = (url) => {
    const githubRegex = /^https:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+(\/?)$/;
    return githubRegex.test(url);
  };
  
  export const isValidZipFile = (file) => {
    if (!file) return false;
    
    const allowedTypes = ['application/zip', 'application/x-zip-compressed'];
    const isZipType = allowedTypes.includes(file.type);
    const isZipExtension = file.name.toLowerCase().endsWith('.zip');
    
    return isZipType || isZipExtension;
  };
  
  export const validateFileSize = (file, maxSizeMB = 100) => {
    if (!file) return false;
    const maxSize = maxSizeMB * 1024 * 1024; // Convert MB to bytes
    return file.size <= maxSize;
  };
  
  export const validateAnalysisStatus = (status) => {
    const validStatuses = [
      'pending',
      'processing',
      'extracting',
      'scanning',
      'generating_report',
      'completed',
      'failed'
    ];
    return validStatuses.includes(status);
  };