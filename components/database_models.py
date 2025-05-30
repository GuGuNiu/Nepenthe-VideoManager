from sqlalchemy import Column, Integer, String, DateTime, func, Table, ForeignKey
from sqlalchemy.orm import relationship
from tools.db_utils import Base

# 视频-标签 关联表 (多对多)
video_tags_table = Table('video_tags', Base.metadata,
    Column('video_id', Integer, ForeignKey('videos.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

# 视频-人物 关联表 (多对多) ---
video_persons_table = Table('video_persons', Base.metadata,
    Column('video_id', Integer, ForeignKey('videos.id'), primary_key=True),
    Column('person_id', Integer, ForeignKey('persons.id'), primary_key=True)
)

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    path = Column(String, unique=True, index=True)
    folder = Column(String, index=True)
    added_date = Column(DateTime(timezone=True), server_default=func.now())
    duration = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    view_count = Column(Integer, default=0)

    tags = relationship("Tag", secondary=video_tags_table, back_populates="videos")
    persons = relationship("Person", secondary=video_persons_table, back_populates="videos") 

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    videos = relationship("Video", secondary=video_tags_table, back_populates="tags")
    def __repr__(self): return f"<Tag(id={self.id}, name='{self.name}')>"

# --- 人物模型 ---
class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # 人物名唯一且不为空
    videos = relationship("Video", secondary=video_persons_table, back_populates="persons")
    def __repr__(self): return f"<Person(id={self.id}, name='{self.name}')>"