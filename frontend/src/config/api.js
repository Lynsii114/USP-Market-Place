// Vercel supplies the deployed API URL; local development keeps its default.
export const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api").replace(/\/+$/, "");
