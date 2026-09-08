import numpy as np
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.database import get_db
from app.models import User, TranscriptSegment, Video, VideoStatus
from app.auth import get_current_user
from app.services.embeddings import embed_text, embedding_from_json

router = APIRouter(prefix="/search", tags=["search"])

# Minimum cosine similarity for a result to count as "relevant".
# Tune this: raise it to be stricter, lower it if too few results show up.
MIN_RELEVANCE_SCORE = 0.35


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr))


@router.get("")
def search(
    q: str = Query(..., min_length=1),
    video_id: Optional[uuid.UUID] = None,
    top_k: int = 8,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantic search over transcript segments.
    - No video_id: global search, grouped by video (one best-matching card per video).
    - With video_id: in-video search, returns every strong match within that video.
    Results below MIN_RELEVANCE_SCORE are dropped entirely rather than
    padding results with weak, unrelated matches.
    """
    query_vector = embed_text(q)

    segments_query = (
        db.query(TranscriptSegment)
        .join(Video, Video.id == TranscriptSegment.video_id)
        .filter(Video.status == VideoStatus.ready)
        .filter(TranscriptSegment.embedding.isnot(None))
    )
    if video_id:
        segments_query = segments_query.filter(TranscriptSegment.video_id == video_id)

    segments = segments_query.all()

    scored = []
    for seg in segments:
        seg_vector = embedding_from_json(seg.embedding)
        score = cosine_similarity(query_vector, seg_vector)
        if score >= MIN_RELEVANCE_SCORE:
            scored.append((score, seg))

    scored.sort(key=lambda x: x[0], reverse=True)

    if video_id:
        top = scored[:top_k]
        return [
            {
                "video_id": str(seg.video_id),
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "text": seg.text,
                "score": round(score, 4),
            }
            for score, seg in top
        ]
    else:
        best_per_video = {}
        for score, seg in scored:
            vid = str(seg.video_id)
            if vid not in best_per_video or score > best_per_video[vid][0]:
                best_per_video[vid] = (score, seg)

        results = sorted(best_per_video.values(), key=lambda x: x[0], reverse=True)[:top_k]

        output = []
        for score, seg in results:
            video = db.query(Video).filter(Video.id == seg.video_id).first()
            output.append({
                "video_id": str(seg.video_id),
                "title": video.title if video else None,
                "category": video.category if video else None,
                "best_match_timestamp": seg.start_time,
                "matched_text": seg.text,
                "score": round(score, 4),
            })
        return output