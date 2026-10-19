const productionApiUrl = "https://usp-market-place-h5f5-gm540cfl3-usp-marketplace.vercel.app/api";
const developmentApiUrl = import.meta.env.VITE_LOCAL_API_URL || "http://localhost:8000/api";

export const API_URL = (import.meta.env.VITE_API_URL || (import.meta.env.DEV ? developmentApiUrl : productionApiUrl)).replace(/\/+$/, "");
