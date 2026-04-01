# question_analyzer.py - Complete question analysis module
import re
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import warnings
warnings.filterwarnings('ignore')

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger', quiet=True)

class QuestionAnalyzer:
    """Analyzes and processes questions from exam papers"""
    
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        
        # Question type patterns
        self.question_patterns = {
            'mcq': r'[A-D]\)|\b[A-D]\.\s|\([A-D]\)|multiple choice|choose the correct',
            'numerical': r'\d+\s*[+\-*/=]|\bcalculate\b|\bcompute\b|\bfind\b.*\bvalue\b|solve|determine',
            'short_answer': r'\bdefine\b|\bwhat is\b|\blist\b|\bname\b|\bstate\b|\bidentify\b',
            'long_answer': r'\bdiscuss\b|\bexplain\b|\belaborate\b|\bdescribe\b|\bcompare\b|\bcontrast\b',
            'diagram': r'\bdraw\b|\bdiagram\b|\bsketch\b|\blabel\b|\billustrate\b',
            'true_false': r'\btrue\b|\bfalse\b|true or false',
            'fill_blank': r'_{3,}|fill in|complete the|blank'
        }
        
        # Bloom's Taxonomy keywords
        self.bloom_keywords = {
            'remember': ['define', 'list', 'name', 'recall', 'state', 'identify', 'what is', 'who', 'when'],
            'understand': ['explain', 'describe', 'discuss', 'summarize', 'paraphrase', 'interpret', 'outline'],
            'apply': ['calculate', 'solve', 'apply', 'use', 'demonstrate', 'implement', 'show', 'compute'],
            'analyze': ['analyze', 'compare', 'contrast', 'differentiate', 'distinguish', 'examine', 'break down'],
            'evaluate': ['evaluate', 'justify', 'critique', 'recommend', 'assess', 'judge', 'prove'],
            'create': ['design', 'create', 'develop', 'formulate', 'propose', 'construct', 'invent']
        }
        
        # Common topics (can be extended)
        self.common_topics = [
            'algorithms', 'data structures', 'programming', 'database', 'networking',
            'operating systems', 'software engineering', 'artificial intelligence',
            'machine learning', 'web development', 'cybersecurity', 'cloud computing'
        ]
    
    def extract_questions(self, text: str) -> list:
        """Extract individual questions from text"""
        questions = []
        
        # Method 1: Look for numbered questions (1., 1), Q1., etc.)
        patterns = [
            r'(?m)^\s*(\d+)[\.\)]\s+(.+?)(?=^\s*\d+[\.\)]|\Z)',
            r'(?m)^\s*Q\.?\s*(\d+)[\.\)]\s+(.+?)(?=^\s*Q\.?\s*\d+[\.\)]|\Z)',
            r'(?m)^\s*([A-Z])[\.\)]\s+(.+?)(?=^\s*[A-Z][\.\)]|\Z)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple) and len(match) > 1:
                    q_text = match[1].strip()
                else:
                    q_text = match.strip() if isinstance(match, str) else str(match)
                
                if len(q_text) > 10:  # Valid question should be longer
                    questions.append(q_text)
        
        # Method 2: Split by question marks if no numbered questions found
        if not questions:
            sentences = sent_tokenize(text)
            for sentence in sentences:
                if '?' in sentence and len(sentence) > 15:
                    questions.append(sentence.strip())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_questions = []
        for q in questions:
            q_lower = q.lower()
            if q_lower not in seen:
                seen.add(q_lower)
                unique_questions.append(q)
        
        return unique_questions
    
    def classify_question_type(self, question: str) -> str:
        """Classify question type based on patterns"""
        question_lower = question.lower()
        
        for q_type, pattern in self.question_patterns.items():
            if re.search(pattern, question_lower, re.IGNORECASE):
                return q_type
        
        # Default classification based on length
        if len(question.split()) < 15:
            return 'short_answer'
        else:
            return 'long_answer'
    
    def extract_topic(self, question: str, possible_topics: list = None) -> str:
        """Extract topic using keyword matching"""
        if possible_topics is None:
            possible_topics = self.common_topics
        
        question_lower = question.lower()
        words = set(word_tokenize(question_lower))
        
        # Score each topic
        topic_scores = {}
        for topic in possible_topics:
            topic_words = set(topic.lower().split())
            score = len(words.intersection(topic_words))
            if score > 0:
                topic_scores[topic] = score
        
        # Return topic with highest score
        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        
        # Try to extract key noun phrases
        try:
            tokens = nltk.word_tokenize(question)
            tagged = nltk.pos_tag(tokens)
            nouns = [word for word, pos in tagged if pos.startswith('NN')]
            if nouns:
                return nouns[0].lower()
        except:
            pass
        
        return 'general'
    
    def determine_bloom_level(self, question: str) -> str:
        """Determine Bloom's Taxonomy level"""
        question_lower = question.lower()
        
        for level, keywords in self.bloom_keywords.items():
            for keyword in keywords:
                if keyword in question_lower:
                    return level
        
        # Default based on question type
        q_type = self.classify_question_type(question)
        if q_type == 'numerical':
            return 'apply'
        elif q_type == 'short_answer':
            return 'remember'
        elif q_type == 'long_answer':
            return 'understand'
        
        return 'understand'
    
    def extract_marks(self, question: str) -> int:
        """Extract marks from question if specified"""
        marks_patterns = [
            r'\((\d+)\s*marks?\)',
            r'\[(\d+)\s*marks?\]',
            r'(\d+)\s*marks?',
            r'(\d+)\s*points?',
            r'(\d+)\s*points?\)'
        ]
        
        for pattern in marks_patterns:
            match = re.search(pattern, question.lower())
            if match:
                try:
                    return int(match.group(1))
                except:
                    pass
        
        # Default marks based on question type
        q_type = self.classify_question_type(question)
        default_marks = {
            'mcq': 1,
            'true_false': 1,
            'fill_blank': 2,
            'short_answer': 5,
            'numerical': 5,
            'diagram': 5,
            'long_answer': 10
        }
        
        return default_marks.get(q_type, 5)
    
    def calculate_similarity(self, q1: str, q2: str) -> float:
        """Calculate semantic similarity between two questions"""
        try:
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform([q1, q2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            return float(similarity[0][0])
        except:
            # Fallback to simple word overlap
            words1 = set(q1.lower().split())
            words2 = set(q2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union) if union else 0.0
    
    def extract_keywords(self, question: str, top_n: int = 5) -> list:
        """Extract keywords from question"""
        question_lower = question.lower()
        words = word_tokenize(question_lower)
        
        # Remove stopwords and punctuation
        keywords = [word for word in words if word.isalnum() and word not in self.stop_words]
        
        # Count frequencies
        freq = Counter(keywords)
        
        # Return top N keywords
        return [word for word, _ in freq.most_common(top_n)]
    
    def analyze_difficulty(self, question: str) -> str:
        """Analyze question difficulty based on complexity"""
        word_count = len(question.split())
        has_bloom = self.determine_bloom_level(question)
        
        if has_bloom in ['create', 'evaluate']:
            return 'hard'
        elif has_bloom in ['apply', 'analyze']:
            return 'medium'
        elif word_count > 30:
            return 'medium'
        else:
            return 'easy'
    
    def get_question_metadata(self, question: str) -> dict:
        """Get complete metadata for a question"""
        return {
            'text': question,
            'type': self.classify_question_type(question),
            'topic': self.extract_topic(question),
            'bloom_level': self.determine_bloom_level(question),
            'marks': self.extract_marks(question),
            'difficulty': self.analyze_difficulty(question),
            'keywords': self.extract_keywords(question),
            'length': len(question.split()),
            'has_question_mark': '?' in question
        }
    
    def find_similar_questions(self, question: str, question_list: list, threshold: float = 0.5) -> list:
        """Find similar questions in a list"""
        similar = []
        for q in question_list:
            similarity = self.calculate_similarity(question, q)
            if similarity > threshold:
                similar.append({
                    'question': q,
                    'similarity': similarity
                })
        
        return sorted(similar, key=lambda x: x['similarity'], reverse=True)
    
    def extract_question_parts(self, question: str) -> dict:
        """Split question into parts (for multi-part questions)"""
        parts = re.split(r'[a-z]\)|\([a-z]\)', question)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) > 1:
            return {
                'is_multipart': True,
                'parts': parts,
                'part_count': len(parts)
            }
        else:
            return {
                'is_multipart': False,
                'text': question
            }


# Simple function-based interface for backward compatibility
def extract_questions(text):
    """Simple function to extract questions"""
    analyzer = QuestionAnalyzer()
    return analyzer.extract_questions(text)

def classify_question_type(question):
    """Simple function to classify question type"""
    analyzer = QuestionAnalyzer()
    return analyzer.classify_question_type(question)

def determine_bloom_level(question):
    """Simple function to determine Bloom's level"""
    analyzer = QuestionAnalyzer()
    return analyzer.determine_bloom_level(question)

def extract_marks(question):
    """Simple function to extract marks"""
    analyzer = QuestionAnalyzer()
    return analyzer.extract_marks(question)


# Test the module
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Question Analyzer")
    print("=" * 60)
    
    analyzer = QuestionAnalyzer()
    
    # Test questions
    test_questions = [
        "1. What is an algorithm? (5 marks)",
        "2. Explain the difference between stack and queue.",
        "3. Calculate the time complexity of bubble sort. [10 marks]",
        "4. Discuss various machine learning algorithms.",
        "5. What are the advantages of Python? (2 marks)"
    ]
    
    print("\nAnalyzing questions:")
    print("-" * 40)
    
    for q in test_questions:
        print(f"\nQuestion: {q}")
        print(f"  Type: {analyzer.classify_question_type(q)}")
        print(f"  Bloom Level: {analyzer.determine_bloom_level(q)}")
        print(f"  Marks: {analyzer.extract_marks(q)}")
        print(f"  Topic: {analyzer.extract_topic(q)}")
        print(f"  Keywords: {analyzer.extract_keywords(q)}")
    
    print("\n" + "=" * 60)
    print("✅ Question Analyzer is working!")