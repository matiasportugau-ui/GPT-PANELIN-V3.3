const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api',
  apiTimeout: import.meta.env.VITE_API_TIMEOUT || 30000,
  openai: {
    apiKey: import.meta.env.VITE_OPENAI_API_KEY || '',
    model: import.meta.env.VITE_OPENAI_MODEL || 'gpt-3.5-turbo',
    maxTokens: parseInt(import.meta.env.VITE_OPENAI_MAX_TOKENS || '2000', 10)
  }
};

export default config;
