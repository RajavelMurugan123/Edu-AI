import whisper

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Video, VideoStatus, TranscriptSegment
from app.services.embeddings import embed_text, embedding_to_json
from app.services.llm import call_llm

_model = None


def get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


def detect_category(full_text: str) -> str:
    """Ask the LLM to pick a short category label from the transcript content."""
    prompt = f"""Based on this video transcript, output ONE short category label
(1-3 words, e.g. "Python", "Java", "Machine Learning", "Web Development", "RAG",
"AI","AI Agents", "SQL", "DevOps"). Pick whatever best fits the actual content.
Return ONLY the category label, nothing else — no punctuation, no explanation.

Transcript:
{full_text[:4000]}

Category:"""
    try:
        category = call_llm(prompt).strip()
        return category[:40] if category else "Uncategorized"
    except Exception:
        return "Uncategorized"


@celery_app.task(name="transcribe_video")
def transcribe_video(video_id: str):
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return

        video.status = VideoStatus.processing
        db.commit()

        file_path = video.file_url.lstrip("/")

        model = get_model()
        result = model.transcribe(file_path, verbose=False)

        db.query(TranscriptSegment).filter(TranscriptSegment.video_id == video.id).delete()

        all_text_parts = []
        for seg in result["segments"]:
            text = seg["text"].strip()
            if not text:
                continue

            vector = embed_text(text)
            all_text_parts.append(text)

            segment = TranscriptSegment(
                video_id=video.id,
                start_time=seg["start"],
                end_time=seg["end"],
                text=text,
                embedding=embedding_to_json(vector),
            )
            db.add(segment)

        db.commit()
        print(f"Saved {len(result['segments'])} segments with embeddings for '{video.title}'")

        # Auto-detect category from the full transcript, but only if the
        # admin left it blank — an admin-provided category is respected.
        if not video.category or video.category.strip() == "":
            full_text = " ".join(all_text_parts)
            video.category = detect_category(full_text)
            print(f"Auto-detected category for '{video.title}': {video.category}")

        video.status = VideoStatus.ready
        db.commit()

    except Exception as e:
        print(f"Transcription failed for {video_id}: {e}")
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = VideoStatus.failed
            db.commit()
    finally:
        db.close()