import axios from "axios";

const api = axios.create({
    baseURL:"http://localhost:2020"
})

export default api;
