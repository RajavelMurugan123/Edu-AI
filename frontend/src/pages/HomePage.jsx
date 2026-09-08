import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { logout } from "../api/auth";
import { listVideos } from "../api/videos";
import { globalSearch } from "../api/search";
import { useNavigate } from "react-router-dom";

export default function HomePage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    listVideos().then(setVideos).finally(() => setLoading(false));
  }, []);

  function handleLogout() {
    logout();
    setUser(null);
    navigate("/login");
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) { setSearchResults(null); return; }
    setSearching(true);
    try {
      setSearchResults(await globalSearch(query));
    } finally {
      setSearching(false);
    }
  }

  function clearSearch() {
    setQuery("");
    setSearchResults(null);
  }

  function formatTime(s) {
    return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Welcome back, {user?.name}</h1>
          <p className="page-subtitle">Browse courses or search across everything you have access to.</p>
        </div>
        <button className="btn" onClick={handleLogout}>Log out</button>
      </div>

      <form onSubmit={handleSearch} className="search-bar" style={{ marginBottom: 28 }}>
        <input
          className="input"
          type="text"
          placeholder="Search all courses, e.g. loops"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button className="btn btn-primary" type="submit" disabled={searching}>
          {searching ? "Searching..." : "Search"}
        </button>
        {searchResults && <button className="btn" type="button" onClick={clearSearch}>Clear</button>}
      </form>

      {searchResults && (
        <div style={{ marginBottom: 32 }}>
          <h3 style={{ fontSize: 15, marginBottom: 14 }}>Search results</h3>
          {searchResults.length === 0 && <p style={{ color: "var(--color-text-secondary)" }}>No matches found.</p>}
          <div className="video-grid">
            {searchResults.map((r) => (
              <div key={r.video_id} className="video-card" onClick={() => navigate(`/watch/${r.video_id}?t=${r.best_match_timestamp}`)}>
                <div className="video-thumb">▶</div>
                <div className="video-card-body">
                  <p className="video-card-title">{r.title}</p>
                  <p className="video-card-meta">{r.category}</p>
                  <p style={{ fontSize: 12, fontStyle: "italic", color: "var(--color-text-secondary)", margin: "6px 0" }}>"{r.matched_text}"</p>
                  <p style={{ fontSize: 12, color: "var(--color-primary)", fontWeight: 600 }}>Jump to {formatTime(r.best_match_timestamp)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!searchResults && (
        <>
          {loading && <p>Loading courses...</p>}
          {!loading && videos.length === 0 && (
            <div className="empty-state">
              <h3>No courses yet</h3>
              <p>Once an admin uploads a video, it will appear here automatically.</p>
            </div>
          )}
          <div className="video-grid">
            {videos.map((v) => (
              <div key={v.id} className="video-card" onClick={() => navigate(`/watch/${v.id}`)}>
                <div className="video-thumb">▶</div>
                <div className="video-card-body">
                  <p className="video-card-title">{v.title}</p>
                  <p className="video-card-meta">{v.category}</p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}