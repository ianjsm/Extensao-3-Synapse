// src/lib/requirements.js
import api from "./api";

export async function startAnalysis(client_request) {
  const res = await api.post("/start_analysis", { client_request });
  return res.data;
}

export async function refine(instruction, history) {
  const res = await api.post("/refine", { instruction, history });
  return res.data;
}

export async function approve(final_requirements, original_request) {
  const res = await api.post("/approve", { final_requirements, original_request });
  return res.data;
}