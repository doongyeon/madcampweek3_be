from sqlalchemy.orm import Session
from models import Song, Lyric
from schemas import SongCreate, LyricCreate

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

def get_songs(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Song).offset(skip).limit(limit).all()

def get_lyrics_by_song_title_and_artist(db: Session, title: str, artist: str):
    song = db.query(Song).filter(Song.title == title, Song.artist == artist).first()
    if song:
        return db.query(Lyric).filter(Lyric.song_id == song.song_id).all()
    return None
