import api from "./client";

export async function sendChatMessage(videoId, message, currentTimestamp) {
  const response = await api.post(`/videos/${videoId}/chat`, {
    message,
    current_timestamp: currentTimestamp,
  });
  return response.data;
}

export async function getVideoSummary(videoId) {
  const response = await api.get(`/videos/${videoId}/summary`);
  return response.data;
}

export async function getRelatedVideos(videoId) {
  const response = await api.get(`/videos/${videoId}/related`);
  return response.data;
}

export async function getSuggestedQuestions(videoId) {
  const response = await api.get(`/videos/${videoId}/suggested-questions`);
  return response.data;
}