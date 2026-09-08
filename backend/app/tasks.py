import whisper

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Video, VideoStatus, TranscriptSegment
from app.services.embeddings import embed_text, embedding_to_json

_model = None


def get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


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

        for seg in result["segments"]:
            text = seg["text"].strip()
            if not text:
                continue

            vector = embed_text(text)

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