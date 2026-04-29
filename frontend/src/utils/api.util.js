import axios from "axios";

const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL ??
    `http://${window.location.hostname || "localhost"}:2020`;

const api = axios.create({
    baseURL: apiBaseUrl
})

export default api;
