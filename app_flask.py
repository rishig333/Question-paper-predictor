# app_flask.py - Complete fixed version
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import json
import tempfile
import uuid
from datetime import datetime

# Import your existing modules
from database import get_session, QuestionPaper, Question, save_paper, save_question, get_all_papers
from ocr_processor import OCRProcessor
from question_analyzer import QuestionAnalyzer
from predictor import QuestionPredictor

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize components
ocr_processor = OCRProcessor(use_easyocr=True)
analyzer = QuestionAnalyzer()
predictor = QuestionPredictor()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Try to import visualization libraries
try:
    import numpy as np
    import pandas as pd
    import plotly
    import plotly.express as px
    PLOTLY_AVAILABLE = True
    print("✅ Visualization libraries loaded")
except ImportError as e:
    print(f"⚠️ Visualization libraries not available: {e}")
    PLOTLY_AVAILABLE = False

# ==================== Routes ====================

@app.route('/')
def index():
    """Home page"""
    papers = get_all_papers()
    stats = {
        'total_papers': len(papers),
        'total_questions': sum(len(p.questions) for p in papers),
        'unique_years': len(set(p.year for p in papers)),
        'unique_subjects': len(set(p.subject for p in papers))
    }
    return render_template('index.html', stats=stats, now=datetime.now())

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload and process question papers"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        files = request.files.getlist('file')
        subject = request.form.get('subject', 'Unknown')
        exam_board = request.form.get('exam_board', 'Unknown')
        year = int(request.form.get('year', datetime.now().year))
        semester = request.form.get('semester', 'Unknown')
        
        processed_count = 0
        errors = []
        
        for file in files:
            if file and allowed_file(file.filename):
                try:
                    # Generate unique filename
                    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    # Process with OCR
                    extracted_text = ocr_processor.extract_text(filepath)
                    
                    if not extracted_text or extracted_text.startswith("Error"):
                        errors.append(f"{file.filename}: {extracted_text}")
                        continue
                    
                    # Save to database
                    paper_id = save_paper(
                        filename=file.filename,
                        subject=subject,
                        exam_board=exam_board,
                        year=year,
                        semester=semester,
                        file_path=filepath,
                        extracted_text=extracted_text
                    )
                    
                    # Extract and save questions
                    questions = analyzer.extract_questions(extracted_text)
                    for q_text in questions:
                        q_type = analyzer.classify_question_type(q_text)
                        bloom_level = analyzer.determine_bloom_level(q_text)
                        marks = analyzer.extract_marks(q_text)
                        topic = analyzer.extract_topic(q_text)
                        
                        save_question(
                            paper_id=paper_id,
                            question_text=q_text,
                            question_type=q_type,
                            marks=marks,
                            topic=topic,
                            bloom_level=bloom_level
                        )
                        
                    
                    processed_count += 1
                    print(f"✅ Processed {file.filename}: {len(questions)} questions")
                    
                except Exception as e:
                    errors.append(f"{file.filename}: {str(e)}")
                    print(f"❌ Error processing {file.filename}: {e}")
        
        if processed_count > 0:
            flash(f'Successfully processed {processed_count} papers!', 'success')
        
        if errors:
            for error in errors[:3]:  # Show first 3 errors
                flash(f'Error: {error}', 'error')
        
        return redirect(url_for('database'))
    
    # GET request - show upload form with current year
    return render_template('upload.html', now=datetime.now())

@app.route('/analytics')
def analytics():
    """Analytics dashboard"""
    papers = get_all_papers()
    
    # Prepare data for charts
    question_types = []
    years = []
    subjects = []
    
    for paper in papers:
        years.append(paper.year)
        subjects.append(paper.subject)
        for q in paper.questions:
            question_types.append(q.question_type)
    
    type_chart = None
    year_chart = None
    
    # Only create charts if plotly is available
    if PLOTLY_AVAILABLE and papers:
        try:
            # Question type distribution chart
            if question_types:
                type_counts = pd.Series(question_types).value_counts()
                fig_types = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    title="Question Types Distribution",
                    color_discrete_sequence=px.colors.sequential.Plasma
                )
                type_chart = json.dumps(fig_types, cls=plotly.utils.PlotlyJSONEncoder)
            
            # Year-wise chart
            if years:
                year_counts = pd.Series(years).value_counts().sort_index()
                fig_years = px.bar(
                    x=year_counts.index,
                    y=year_counts.values,
                    title="Papers per Year",
                    labels={'x': 'Year', 'y': 'Number of Papers'},
                    color=year_counts.values,
                    color_continuous_scale='Viridis'
                )
                year_chart = json.dumps(fig_years, cls=plotly.utils.PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error creating charts: {e}")
    
    return render_template(
        'analytics.html',
        type_chart=type_chart,
        year_chart=year_chart,
        papers_count=len(papers),
        now=datetime.now()
    )

@app.route('/predictions')
def predictions():
    """Show predictions"""
    papers = get_all_papers()
    
    if not papers:
        flash('No papers in database. Upload some papers first.', 'warning')
        return redirect(url_for('upload'))
    
    try:
        # Prepare training data
        training_data = []
        for paper in papers:
            for q in paper.questions:
                training_data.append({
                    'topic': q.topic,
                    'year': paper.year,
                    'question_text': q.question_text,
                    'question_type': q.question_type,
                    'bloom_level': q.bloom_level,
                    'marks': q.marks,
                    'frequency_score': q.frequency_score
                })
        
        # Analyze trends and make predictions
        trends = predictor.analyze_historical_data(training_data)
        predictor.train_model(training_data)
        
        # Get latest questions for prediction
        current_questions = []
        latest_year = max([p.year for p in papers])
        for paper in papers:
            if paper.year == latest_year:
                for q in paper.questions:
                    current_questions.append({
                        'question_text': q.question_text,
                        'topic': q.topic,
                        'question_type': q.question_type,
                        'marks': q.marks,
                        'bloom_level': q.bloom_level,
                        'year': paper.year
                    })
        
        predictions_list = predictor.predict_likely_questions(
            current_questions, trends, year=2026
        )
        
        return render_template('predictions.html', predictions=predictions_list, now=datetime.now())
        
    except Exception as e:
        print(f"Error generating predictions: {e}")
        flash(f'Error generating predictions: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/database')
def database():
    """View database contents"""
    papers = get_all_papers()
    years = sorted(set(p.year for p in papers), reverse=True)
    return render_template('database.html', papers=papers, years=years, now=datetime.now())

@app.route('/api/paper/<int:paper_id>')
def api_paper_detail(paper_id):
    """API endpoint to get paper details"""
    session = get_session()
    paper = session.query(QuestionPaper).get(paper_id)
    if not paper:
        return jsonify({'error': 'Paper not found'}), 404
    
    questions = []
    for q in paper.questions:
        questions.append({
            'id': q.id,
            'text': q.question_text[:200] + '...' if len(q.question_text) > 200 else q.question_text,
            'type': q.question_type,
            'marks': q.marks,
            'topic': q.topic,
            'bloom_level': q.bloom_level
        })
    
    return jsonify({
        'id': paper.id,
        'filename': paper.filename,
        'subject': paper.subject,
        'year': paper.year,
        'exam_board': paper.exam_board,
        'semester': paper.semester,
        'extracted_text': paper.extracted_text[:1000] + '...' if paper.extracted_text else '',
        'questions': questions
    })

@app.route('/api/delete_paper/<int:paper_id>', methods=['POST'])
def delete_paper(paper_id):
    """Delete a paper"""
    session = get_session()
    paper = session.query(QuestionPaper).get(paper_id)
    if paper:
        if os.path.exists(paper.file_path):
            os.remove(paper.file_path)
        session.delete(paper)
        session.commit()
        flash('Paper deleted successfully', 'success')
    else:
        flash('Paper not found', 'error')
    
    return redirect(url_for('database'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', now=datetime.now()), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html', now=datetime.now()), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Starting Question Paper Predictor")
    print("=" * 50)
    print(f"📁 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"🌐 Server: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)