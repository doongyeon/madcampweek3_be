from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import crud, models, schemas
from database import SessionLocal, engine
from typing import List
import re
from schemas import LanguageTypeEnum
from translate import translate_lyrics

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def read_root():
    return templates.TemplateResponse("upload.html", {"request": {}})

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    nickname: str = Form(...),
    language_type: str = Form(...),
):
    contents = await file.read()
    content_str = contents.decode('utf-8')

    title = extract_tag(content_str, 'ti')
    artist = extract_tag(content_str, 'ar')
    album = extract_tag(content_str, 'al')

    if not title or not artist:
        raise HTTPException(status_code=400, detail="Title and artist must be specified either in the form or the LRC file")

    lyrics = parse_lrc(content_str)
    song_data = schemas.SongCreate(
        title=title,
        artist=artist,
        nickname=nickname,
        language_type=language_type,
        album=album,
        likes=0,
        dislikes=0,
        lyrics=lyrics
    )
    db = next(get_db())
    created_song = crud.create_song(db=db, song=song_data)

    if language_type == "Both":
        translated_lyrics = parse_translated_lrc(content_str)
        crud.create_translated_lyrics(
            db=db, 
            song_id=created_song.song_id, 
            translated_lyrics=[
                schemas.TranslatedLyricCreate(
                    timestamp=tl.timestamp, 
                    original_lyrics=tl.original_lyrics, 
                    translated_lyrics=tl.translated_lyrics
                ) for tl in translated_lyrics
            ]
        )

    return {"filename": file.filename}

def truncate_timestamp(timestamp: str) -> str:
    if "." in timestamp:
        return timestamp.split(".")[0]
    return timestamp

@app.get("/lyrics", response_model=List[schemas.TranslatedLyricBase])
def read_lyrics(title: str = Query(...), artist: str = Query(...), db: Session = Depends(get_db)):
    song = db.query(models.Song).filter(models.Song.title == title, models.Song.artist == artist).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    lyrics = crud.get_lyrics_by_song_title_and_artist(db, title, artist)
    if not lyrics:
        raise HTTPException(status_code=404, detail="Lyrics not found")
    
    print(f"Song language type: {song.language_type}")

    if str(song.language_type) == "LanguageType.Foreign":
        translated_lyrics = translate_lyrics([schemas.LyricCreate(timestamp=l.timestamp, lyrics=l.lyrics) for l in lyrics])
        combined_lyrics = [
            schemas.TranslatedLyricBase(
                timestamp=truncate_timestamp(l.timestamp),
                original_lyrics=l.lyrics,
                translated_lyrics=t.lyrics
            )
            for l, t in zip(lyrics, translated_lyrics)
        ]
        return combined_lyrics
    
    if str(song.language_type) == "LanguageType.Both":
        translated_lyrics = db.query(models.TranslatedLyric).filter(models.TranslatedLyric.song_id == song.song_id).all()
        combined_lyrics = [
            schemas.TranslatedLyricBase(
                timestamp=truncate_timestamp(tl.timestamp),
                original_lyrics=tl.original_lyrics,
                translated_lyrics=tl.translated_lyrics
            )
            for tl in translated_lyrics
        ]
        return combined_lyrics



    combined_lyrics = [
        schemas.TranslatedLyricBase(
            timestamp=truncate_timestamp(l.timestamp),
            original_lyrics=l.lyrics,
            translated_lyrics=""
        )
        for l in lyrics
    ]
    return combined_lyrics

def parse_lrc(content: str) -> List[schemas.LyricCreate]:
    lines = content.splitlines()
    parsed_lyrics = []
    for line in lines:
        time_lyrics = re.findall(r'\[(\d{2}:\d{2}\.\d{2})\](.*)', line)
        if time_lyrics:
            for timestamp, lyric in time_lyrics:
                parsed_lyrics.append(schemas.LyricCreate(timestamp=timestamp, lyrics=lyric.strip()))
    return parsed_lyrics

def parse_translated_lrc(content: str) -> List[schemas.TranslatedLyricCreate]:
    lines = content.splitlines()
    parsed_lyrics = []
    current_timestamp = ""
    original_lyrics = ""
    translated_lyrics = ""
    for line in lines:
        if line.startswith("["):
            time_lyrics = re.findall(r'\[(\d{2}:\d{2}\.\d{2})\](.*)', line)
            if time_lyrics:
                if current_timestamp and original_lyrics:
                    parsed_lyrics.append(
                        schemas.TranslatedLyricCreate(
                            timestamp=current_timestamp,
                            original_lyrics=original_lyrics.strip(),
                            translated_lyrics=translated_lyrics.strip()
                        )
                    )
                current_timestamp, original_lyrics = time_lyrics[0]
                translated_lyrics = ""
        else:
            translated_lyrics += line + " "
    if current_timestamp and original_lyrics:
        parsed_lyrics.append(
            schemas.TranslatedLyricCreate(
                timestamp=current_timestamp,
                original_lyrics=original_lyrics.strip(),
                translated_lyrics=translated_lyrics.strip()
            )
        )
    return parsed_lyrics

def extract_tag(content: str, tag: str) -> str:
    match = re.search(rf'\[{tag}:(.*?)\]', content)
    return match.group(1) if match else None
