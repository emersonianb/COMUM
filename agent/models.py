# agent/models.py
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    level = Column(String, nullable=True)
    module = Column(String, nullable=True)

class History(Base):
    __tablename__ = "histories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.now)
    message = Column(Text)

class LearningState(Base):
    __tablename__ = "learning_states"
    
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    level = Column(String, nullable=True)
    current_module = Column(String, nullable=True)
    last_topic = Column(String, nullable=True)
    current_category = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class TaughtWord(Base):
    __tablename__ = "taught_words"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    word = Column(String)

class TaughtTopic(Base):
    __tablename__ = "taught_topics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    topic = Column(String)

class TopicProgress(Base):
    __tablename__ = "topic_progress"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    class_id = Column(String)
    topic = Column(String)
    status = Column(String)
    last_review = Column(DateTime, default=datetime.now)
    attempts = Column(Integer, default=1)
    confidence = Column(Float, nullable=True)

class UserMaterial(Base):
    __tablename__ = "user_materials"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    category = Column(String)  # 'conversacao', 'gramatica', 'vocabulario'
    topic = Column(String)     # Tema retornado pelo LLM
    content = Column(Text)     # Conteúdo extraído
    created_at = Column(DateTime, default=datetime.now)

class TeacherClass(Base):
    __tablename__ = "teacher_classes"
    
    id = Column(String, primary_key=True)  # ex: "class_01"
    teacher_id = Column(String, default="prof_01")
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)

class TeacherTopic(Base):
    __tablename__ = "teacher_topics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(String, ForeignKey("teacher_classes.id"))
    name = Column(String)  # Nome do tópico ou conceito