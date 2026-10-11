const productionApiUrl = "https://usp-market-place-h5f5-gm540cfl3-usp-marketplace.vercel.app/api";
const defaultApiUrl = import.meta.env.DEV ? "http://localhost:8000/api" : productionApiUrl;

export const API_URL = (import.meta.env.VITE_API_URL || defaultApiUrl).replace(/\/+$/, "");
