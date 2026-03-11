import axios from "axios";

const api = axios.create({
    baseURL:"http://localhost:2020"
})

api.interceptors.request.use((config) => {
    const stored = localStorage.getItem("token");
    if (stored) {
        // Support both raw token and JSON-stringified token
        let token = stored;
        try {
            token = JSON.parse(stored);
        } catch {
            // stored was already a plain string, ignore parse error
        }
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
})

export default api;