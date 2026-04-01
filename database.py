# database.py - Complete version with all required functions
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

class QuestionPaper(Base):
    __tablename__ = 'question_papers'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255))
    subject = Column(String(100))
    exam_board = Column(String(100))
    year = Column(Integer)
    semester = Column(String(50))
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String(500))
    extracted_text = Column(Text)
    
    questions = relationship("Question", back_populates="paper", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, ForeignKey('question_papers.id', ondelete='CASCADE'))
    question_text = Column(Text)
    question_type = Column(String(50))
    marks = Column(Integer, default=5)
    topic = Column(String(200), default="general")
    bloom_level = Column(String(50), default="understand")
    frequency_score = Column(Float, default=1.0)
    
    paper = relationship("QuestionPaper", back_populates="questions")
    predictions = relationship("Prediction", back_populates="question", cascade="all, delete-orphan")

class Prediction(Base):
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id', ondelete='CASCADE'))
    predicted_year = Column(Integer)
    confidence_score = Column(Float)
    model_version = Column(String(50))
    prediction_date = Column(DateTime, default=datetime.utcnow)
    
    question = relationship("Question", back_populates="predictions")

class TopicPattern(Base):
    __tablename__ = 'topic_patterns'
    
    id = Column(Integer, primary_key=True)
    subject = Column(String(100))
    topic = Column(String(200))
    avg_frequency = Column(Float)
    last_appeared = Column(Integer)
    trend_direction = Column(String(20))

# Database setup
engine = create_engine('sqlite:///question_papers.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)

# Session factory
Session = sessionmaker(bind=engine)

def get_session():
    """Get a database session"""
    return Session()

def save_paper(filename, subject, exam_board, year, semester, file_path, extracted_text):
    """Save a question paper to database"""
    session = get_session()
    try:
        paper = QuestionPaper(
            filename=filename,
            subject=subject,
            exam_board=exam_board,
            year=year,
            semester=semester,
            file_path=file_path,
            extracted_text=extracted_text
        )
        session.add(paper)
        session.commit()
        return paper.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def save_question(paper_id, question_text, question_type, marks, topic, bloom_level):
    """Save a question to database"""
    session = get_session()
    try:
        question = Question(
            paper_id=paper_id,
            question_text=question_text,
            question_type=question_type,
            marks=marks,
            topic=topic,
            bloom_level=bloom_level
        )
        session.add(question)
        session.commit()
        return question.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_all_papers():
    """Get all question papers from database"""
    session = get_session()
    try:
        return session.query(QuestionPaper).order_by(QuestionPaper.year.desc()).all()
    finally:
        session.close()

def get_paper_by_id(paper_id):
    """Get a specific paper by ID"""
    session = get_session()
    try:
        return session.query(QuestionPaper).get(paper_id)
    finally:
        session.close()

def get_questions_by_paper(paper_id):
    """Get all questions for a specific paper"""
    session = get_session()
    try:
        return session.query(Question).filter(Question.paper_id == paper_id).all()
    finally:
        session.close()

def get_questions_by_topic(topic):
    """Get all questions by topic"""
    session = get_session()
    try:
        return session.query(Question).filter(Question.topic == topic).all()
    finally:
        session.close()

def update_question_frequency(question_id, frequency_score):
    """Update frequency score for a question"""
    session = get_session()
    try:
        question = session.query(Question).get(question_id)
        if question:
            question.frequency_score = frequency_score
            session.commit()
    finally:
        session.close()

def delete_paper(paper_id):
    """Delete a paper and its questions"""
    session = get_session()
    try:
        paper = session.query(QuestionPaper).get(paper_id)
        if paper:
            session.delete(paper)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_statistics():
    """Get database statistics"""
    session = get_session()
    try:
        total_papers = session.query(QuestionPaper).count()
        total_questions = session.query(Question).count()
        unique_years = session.query(QuestionPaper.year).distinct().count()
        unique_subjects = session.query(QuestionPaper.subject).distinct().count()
        
        return {
            'total_papers': total_papers,
            'total_questions': total_questions,
            'unique_years': unique_years,
            'unique_subjects': unique_subjects
        }
    finally:
        session.close()

def search_questions(keyword):
    """Search questions by keyword"""
    session = get_session()
    try:
        return session.query(Question).filter(
            Question.question_text.contains(keyword)
        ).all()
    finally:
        session.close()