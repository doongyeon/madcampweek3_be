from pydantic import BaseModel
from typing import List, Optional
import enum

class LanguageTypeEnum(str, enum.Enum):
    Korean = "Korean"
    Foreign = "Foreign"
    Both = "Both"

class LyricBase(BaseModel):
    timestamp: str
    lyrics: str

class LyricCreate(LyricBase):
    pass

class Lyric(LyricBase):
    id: int
    song_id: int

    class Config:
        from_attributes = True

class TranslatedLyricBase(BaseModel):
    timestamp: str
    original_lyrics: str
    translated_lyrics: str

class TranslatedLyricCreate(TranslatedLyricBase):
    pass

class TranslatedLyric(TranslatedLyricBase):
    id: int
    song_id: int

    class Config:
        from_attributes = True

class SongBase(BaseModel):
    title: str
    artist: Optional[str] = None
    nickname: str
    language_type: LanguageTypeEnum
    album: Optional[str] = None
    likes: int = 0
    dislikes: int = 0

class SongCreate(SongBase):
    lyrics: List[LyricCreate]

class Song(SongBase):
    song_id: int
    lyrics: List[Lyric] = []

    class Config:
        from_attributes = True
