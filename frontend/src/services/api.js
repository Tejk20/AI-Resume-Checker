import axios from "axios";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1",
  timeout: 60000,
});
export function errorMessage(error) {
  const detail = error.response?.data?.detail;
  return typeof detail === "string"
    ? detail
    : Array.isArray(detail)
      ? detail.map((x) => x.msg).join("; ")
      : "Could not reach the server. Check that the backend is running, then retry.";
}
