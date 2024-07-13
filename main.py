from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import crud, models, schemas
from database import SessionLocal, engine
from typing import List
import re

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
    title: str = Form(...),
    artist: str = Form(...),
    nickname: str = Form(...),
    language_type: str = Form(...),
    album: str = Form(None),
    file: UploadFile = File(...)
):
    contents = await file.read()
    lyrics = parse_lrc(contents.decode('utf-8'))
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
    crud.create_song(db=db, song=song_data)
    return {"filename": file.filename}

def parse_lrc(content: str) -> List[schemas.LyricCreate]:
    lines = content.splitlines()
    parsed_lyrics = []
    for line in lines:
        time_lyrics = re.findall(r'\[(\d{2}:\d{2}\.\d{2})\](.*)', line)
        if time_lyrics:
            for timestamp, lyric in time_lyrics:
                parsed_lyrics.append(schemas.LyricCreate(timestamp=timestamp, lyrics=lyric.strip()))
    return parsed_lyrics

@app.get("/lyrics", response_model=List[schemas.Lyric])
def read_lyrics(title: str = Query(...), artist: str = Query(...), db: Session = Depends(get_db)):
    lyrics = crud.get_lyrics_by_song_title_and_artist(db, title, artist)
    if not lyrics:
        raise HTTPException(status_code=404, detail="Lyrics not found")
    return lyrics
