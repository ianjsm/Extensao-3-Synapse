import api from "./api";

export async function startAudioChat(formData) {
  const res = await api.post("/audio_chat", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}