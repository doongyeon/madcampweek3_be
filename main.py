from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
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

app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    # 변경된 부분: success 변수를 추가하여 템플릿으로 전달
    return templates.TemplateResponse("upload.html", {"request": request, "success": False})

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

    return {"success": True}

def truncate_timestamp(timestamp: str) -> str:
    if "." in timestamp:
        return timestamp.split(".")[0]
    return timestamp

@app.get("/lyrics", response_model=List[schemas.TranslatedLyricBase])
def read_lyrics(title: str = Query(...), artist: str = Query(...), db: Session = Depends(get_db)):
    songs = db.query(models.Song).filter(models.Song.title == title, models.Song.artist == artist).all()
    if not songs:
        raise HTTPException(status_code=404, detail="Song not found")

    # "Both" language_type을 가진 노래를 우선적으로 선택
    song = next((s for s in songs if s.language_type == models.LanguageType.Both), songs[0])

    lyrics = crud.get_lyrics_by_song_id(db, song.song_id)
    if not lyrics:
        raise HTTPException(status_code=404, detail="Lyrics not found")

    print(f"Song language type: {song.language_type}")

    if str(song.language_type) == "LanguageType.Both":
        translated_lyrics = db.query(models.TranslatedLyric).filter(models.TranslatedLyric.song_id == song.song_id).all()
        combined_lyrics = [
            schemas.TranslatedLyricBase(
                timestamp=truncate_timestamp(tl.timestamp),
                original=tl.original_lyrics,
                translated=tl.translated_lyrics
            )
            for tl in translated_lyrics
        ]
        return combined_lyrics

    if str(song.language_type) == "LanguageType.Foreign":
        translated_lyrics = translate_lyrics([schemas.LyricCreate(timestamp=l.timestamp, lyrics=l.lyrics) for l in lyrics])
        combined_lyrics = [
            schemas.TranslatedLyricBase(
                timestamp=truncate_timestamp(l.timestamp),
                original=l.lyrics,
                translated=t.lyrics
            )
            for l, t in zip(lyrics, translated_lyrics)
        ]
        return combined_lyrics

    combined_lyrics = [
        schemas.TranslatedLyricBase(
            timestamp=truncate_timestamp(l.timestamp),
            original=l.lyrics,
            translated=""
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



@app.get("/songs", response_class=HTMLResponse)
def read_songs_page(request: Request, db: Session = Depends(get_db)):
    songs = crud.get_songs(db)
    return templates.TemplateResponse("songs.html", {"request": request, "songs": songs})

@app.get("/api/songs", response_model=List[schemas.Song])
def read_songs(query: str = "", skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    if query:
        songs = db.query(models.Song).filter(
            (models.Song.title.contains(query)) |
            (models.Song.artist.contains(query))
        ).offset(skip).limit(limit).all()
    else:
        songs = crud.get_songs(db, skip=skip, limit=limit)
    return songs

@app.post("/like/{song_id}")
def like_song(song_id: int, db: Session = Depends(get_db)):
    song = crud.get_song(db, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    song.likes += 1
    db.commit()
    db.refresh(song)
    return {"success": True, "likes": song.likes}

@app.post("/dislike/{song_id}")
def dislike_song(song_id: int, db: Session = Depends(get_db)):
    song = crud.get_song(db, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    song.dislikes += 1
    db.commit()
    db.refresh(song)
    return {"success": True, "dislikes": song.dislikes}


@app.get("/lyrics/{song_id}", response_class=HTMLResponse)
def read_lyrics_page(request: Request, song_id: int, db: Session = Depends(get_db)):
    song = crud.get_song(db, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    lyrics = crud.get_lyrics_by_song_id(db, song_id)
    if song.language_type == models.LanguageType.Both:
        translated_lyrics = crud.get_translated_lyrics(db, song_id)
        for lyric, translated_lyric in zip(lyrics, translated_lyrics):
            lyric.translated = translated_lyric.translated_lyrics  # translated_lyrics를 translated로 매핑

    for lyric in lyrics:
        print(f"Timestamp: {lyric.timestamp}, Lyrics: {lyric.lyrics}, Translated: {getattr(lyric, 'translated', None)}")

    return templates.TemplateResponse("lyrics.html", {"request": request, "song": song, "lyrics": lyrics, "language_type": str(song.language_type)})