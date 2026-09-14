import { useEffect, useState } from "react";
import AdminLayout from "../components/AdminLayout";
import { adminListAllVideos, uploadVideo, deleteVideo } from "../api/videos";

export default function AdminDashboard() {
  const [videos, setVideos] = useState([]);
  const [form, setForm] = useState({ title: "", description: "", category: "", file: null });
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  async function refresh() {
    setVideos(await adminListAllVideos());
  }

  useEffect(() => { refresh(); }, []);

  async function handleUpload(e) {
    e.preventDefault();
    setError("");
    if (!form.title || !form.file) {
      setError("Title and a video file are required.");
      return;
    }
    setUploading(true);
    try {
      await uploadVideo(form);
      setForm({ title: "", description: "", category: "", file: null });
      e.target.reset();
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id) {
    await deleteVideo(id);
    refresh();
  }

  const readyCount = videos.filter((v) => v.status === "ready").length;
  const processingCount = videos.filter((v) => v.status === "processing" || v.status === "uploading").length;
  const failedCount = videos.filter((v) => v.status === "failed").length;

  return (
    <AdminLayout>
      <div className="page">
        <div className="page-header">
          <div>
            <h1 className="page-title">Videos</h1>
            <p className="page-subtitle">Upload course content — any format, processed automatically.</p>
          </div>
        </div>

        <div className="stat-grid">
          <div className="stat-card">
            <p className="stat-label">Total videos</p>
            <p className="stat-value">{videos.length}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Ready</p>
            <p className="stat-value" style={{ color: "var(--color-success)" }}>{readyCount}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Processing</p>
            <p className="stat-value" style={{ color: "var(--color-warning)" }}>{processingCount}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Failed</p>
            <p className="stat-value" style={{ color: "var(--color-danger)" }}>{failedCount}</p>
          </div>
        </div>

        <div className="card card-pad" style={{ marginBottom: 24 }}>
          <p className="section-label" style={{ marginBottom: 16 }}>Upload a new video</p>
          <form onSubmit={handleUpload} className="form-row">
            <input className="input" placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <input className="input" placeholder="Category (optional — AI detects it if left blank)" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
            <input className="input" placeholder="Description (optional)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <input type="file" accept="video/*" onChange={(e) => setForm({ ...form, file: e.target.files[0] })} />
            <button className="btn btn-primary" type="submit" disabled={uploading}>
              {uploading ? "Uploading..." : "+ Upload video"}
            </button>
          </form>
          {error && <p className="error-text" style={{ margin: 0 }}>{error}</p>}
        </div>

        <div className="card">
          {videos.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">▶</div>
              <h3>Upload your first video</h3>
              <p>Videos you upload appear here and on the learner Home page once processing finishes.</p>
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr><th>Title</th><th>Category</th><th>Status</th><th></th></tr>
              </thead>
              <tbody>
                {videos.map((v) => (
                  <tr key={v.id}>
                    <td style={{ fontWeight: 600 }}>{v.title}</td>
                    <td>{v.category || "—"}</td>
                    <td><span className={`badge badge-${v.status}`}>{v.status}</span></td>
                    <td style={{ textAlign: "right" }}>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(v.id)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}