from sqlalchemy.orm import Session
from models import Song, Lyric, TranslatedLyric
from schemas import SongCreate, LyricCreate, TranslatedLyricCreate
from typing import List  # 추가된 부분

def create_song(db: Session, song: SongCreate):
    db_song = Song(
        title=song.title,
        artist=song.artist,
        nickname=song.nickname,
        language_type=song.language_type,
        album=song.album,
        likes=song.likes,
        dislikes=song.dislikes
    )
    db.add(db_song)
    db.commit()
    db.refresh(db_song)

    for lyric in song.lyrics:
        db_lyric = Lyric(
            song_id=db_song.song_id,
            timestamp=lyric.timestamp,
            lyrics=lyric.lyrics
        )
        db.add(db_lyric)
    db.commit()
    return db_song

def get_song(db: Session, song_id: int):
    return db.query(Song).filter(Song.song_id == song_id).first()

def get_songs(db: Session, skip: int = 0, limit: int = None):  # limit의 기본값을 None으로 설정
    query = db.query(Song).offset(skip)
    if limit:
        query = query.limit(limit)
    return query.all()

def get_lyrics_by_song_id(db: Session, song_id: int):
    return db.query(Lyric).filter(Lyric.song_id == song_id).all()

def create_translated_lyrics(db: Session, song_id: int, translated_lyrics: List[TranslatedLyricCreate]):
    for translated_lyric in translated_lyrics:
        db_translated_lyric = TranslatedLyric(
            song_id=song_id,
            timestamp=translated_lyric.timestamp,
            original=translated_lyric.original_lyrics,
            translated=translated_lyric.translated_lyrics
        )
        db.add(db_translated_lyric)
    db.commit()

def get_translated_lyrics(db: Session, song_id: int):
    return db.query(TranslatedLyric).filter(TranslatedLyric.song_id == song_id).all()