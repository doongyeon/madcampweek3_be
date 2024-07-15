from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
import enum

class LanguageType(enum.Enum):
    Korean = "Korean"
    Foreign = "Foreign"
    Both = "Both"

class Song(Base):
    __tablename__ = "Songs"

    song_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    artist = Column(String(255))
    nickname = Column(String(255), nullable=False)
    language_type = Column(Enum(LanguageType), nullable=False)
    album = Column(String(255))
    likes = Column(Integer, default=0)  # 좋아요 필드 추가
    dislikes = Column(Integer, default=0)  # 싫어요 필드 추가

    lyrics = relationship("Lyric", back_populates="song")
    translated_lyrics = relationship("TranslatedLyric", back_populates="song")

class Lyric(Base):
    __tablename__ = "Lyrics"

    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey('Songs.song_id'), nullable=False)
    timestamp = Column(String(10), nullable=False)
    lyrics = Column(Text, nullable=False)

    song = relationship("Song", back_populates="lyrics")

class TranslatedLyric(Base):
    __tablename__ = "TranslatedLyrics"

    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey('Songs.song_id'), nullable=False)
    timestamp = Column(String(10), nullable=False)
    original_lyrics = Column(Text, nullable=False)
    translated_lyrics = Column(Text, nullable=False)

    song = relationship("Song", back_populates="translated_lyrics")
