import api from "./client";

export async function listVideos() {
  const response = await api.get("/videos");
  return response.data;
}

export async function getVideo(videoId) {
  const response = await api.get(`/videos/${videoId}`);
  return response.data;
}

export async function adminListAllVideos() {
  const response = await api.get("/videos/admin/all");
  return response.data;
}

export async function uploadVideo({ title, description, category, file }) {
  const formData = new FormData();
  formData.append("title", title);
  formData.append("description", description || "");
  formData.append("category", category);
  formData.append("file", file);

  const response = await api.post("/videos/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function deleteVideo(videoId) {
  await api.delete(`/videos/${videoId}`);
}

export async function getVideoTranscript(videoId) {
  const response = await api.get(`/videos/${videoId}/transcript`);
  return response.data;
}