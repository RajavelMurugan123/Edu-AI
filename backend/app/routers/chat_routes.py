import os
import json
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.models import User, TranscriptSegment, Video, VideoStatus
from app.auth import get_current_user
from app.services.embeddings import embed_text, embedding_from_json

router = APIRouter(prefix="/videos", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    current_timestamp: float | None = None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    return float(np.dot(np.array(a), np.array(b)))


def call_llm(prompt: str) -> str:
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


@router.post("/{video_id}/chat")
def chat_with_video(
    video_id: uuid.UUID,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video = db.query(Video).filter(Video.id == video_id, Video.status == VideoStatus.ready).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found or not ready")

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.video_id == video_id)
        .filter(TranscriptSegment.embedding.isnot(None))
        .all()
    )
    if not segments:
        raise HTTPException(status_code=400, detail="This video has no transcript yet")

    query_vector = embed_text(payload.message)

    scored = []
    for seg in segments:
        seg_vector = embedding_from_json(seg.embedding)
        score = cosine_similarity(query_vector, seg_vector)
        scored.append((score, seg))
    scored.sort(key=lambda x: x[0], reverse=True)

    top_segments = [seg for _, seg in scored[:10]]
    top_segments.sort(key=lambda s: s.start_time)

    context = "\n".join(f"[{int(s.start_time)}s] {s.text}" for s in top_segments)

    prompt = f"""You are a helpful assistant answering questions about a video, using ONLY the transcript excerpts below.

Format your answer using Markdown:
- Use **bold** for key terms, tool names, or concepts.
- Use bullet points when listing multiple items.
- When citing something specific, include the timestamp range in parentheses like (8:28 - 9:51), converting seconds to minutes:seconds format.
- If the answer isn't in the transcript, say so honestly rather than guessing.

Transcript excerpts:
{context}

Question: {payload.message}

Answer:"""

    answer = call_llm(prompt)

    return {
        "answer": answer,
        "referenced_timestamps": [s.start_time for s in top_segments],
    }


@router.get("/{video_id}/summary")
def summarize_video(
    video_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video = db.query(Video).filter(Video.id == video_id, Video.status == VideoStatus.ready).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found or not ready")

    if video.cached_summary:
        return {"summary": video.cached_summary}

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.video_id == video_id)
        .order_by(TranscriptSegment.start_time)
        .all()
    )
    if not segments:
        raise HTTPException(status_code=400, detail="This video has no transcript yet")

    full_text = " ".join(s.text for s in segments)

    prompt = f"""Summarize this video transcript in 3-4 short sentences aimed at a student deciding whether to watch it. Be concrete about what topics are covered.

Transcript:
{full_text[:6000]}

Summary:"""

    summary = call_llm(prompt)

    video.cached_summary = summary
    db.commit()

    return {"summary": summary}


@router.get("/{video_id}/related")
def related_videos(
    video_id: uuid.UUID,
    top_k: int = 4,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.video_id == video_id)
        .filter(TranscriptSegment.embedding.isnot(None))
        .all()
    )
    if not target_segments:
        return []

    target_vectors = [embedding_from_json(s.embedding) for s in target_segments]
    target_avg = np.mean(target_vectors, axis=0)

    other_videos = db.query(Video).filter(Video.id != video_id, Video.status == VideoStatus.ready).all()

    scored = []
    for v in other_videos:
        v_segments = (
            db.query(TranscriptSegment)
            .filter(TranscriptSegment.video_id == v.id)
            .filter(TranscriptSegment.embedding.isnot(None))
            .all()
        )
        if not v_segments:
            continue
        v_vectors = [embedding_from_json(s.embedding) for s in v_segments]
        v_avg = np.mean(v_vectors, axis=0)
        score = float(np.dot(target_avg, v_avg) / (np.linalg.norm(target_avg) * np.linalg.norm(v_avg)))
        scored.append((score, v))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    return [
        {"video_id": str(v.id), "title": v.title, "category": v.category, "score": round(score, 4)}
        for score, v in top
    ]


@router.get("/{video_id}/suggested-questions")
def suggested_questions(
    video_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video = db.query(Video).filter(Video.id == video_id, Video.status == VideoStatus.ready).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found or not ready")

    if video.cached_suggested_questions:
        return {"questions": json.loads(video.cached_suggested_questions)}

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.video_id == video_id)
        .order_by(TranscriptSegment.start_time)
        .all()
    )
    if not segments:
        return {"questions": []}

    full_text = " ".join(s.text for s in segments)

    prompt = f"""Based on this video transcript, write exactly 3 short questions a curious viewer would naturally ask about it. Each question should be under 8 words. Return ONLY the questions, one per line, no numbering, no extra text.

Transcript:
{full_text[:6000]}

Questions:"""

    raw = call_llm(prompt)
    questions = [q.strip("- ").strip() for q in raw.strip().split("\n") if q.strip()][:3]

    video.cached_suggested_questions = json.dumps(questions)
    db.commit()

    return {"questions": questions}