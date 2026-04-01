# predictor.py - Complete prediction module
import numpy as np
import pandas as pd
from collections import defaultdict, Counter
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import joblib
import os
import json
import warnings
warnings.filterwarnings('ignore')

class QuestionPredictor:
    """Predicts likely questions for upcoming exams"""
    
    def __init__(self):
        self.topic_frequencies = defaultdict(list)
        self.year_range = []
        self.model = None
        self.label_encoders = {}
        self.topic_trends = {}
        self.question_patterns = {}
        
    def analyze_historical_data(self, questions_data):
        """
        Analyze historical question patterns
        
        Args:
            questions_data: list of dicts with keys - topic, year, question_text, question_type, marks
            
        Returns:
            Dictionary of trends for each topic
        """
        if not questions_data:
            return {}
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(questions_data)
        
        # Calculate topic frequencies by year
        topic_year_counts = df.groupby(['topic', 'year']).size().unstack(fill_value=0)
        
        # Calculate trends for each topic
        trends = {}
        for topic in topic_year_counts.index:
            counts = topic_year_counts.loc[topic].values
            years = topic_year_counts.loc[topic].index.values
            
            if len(counts) > 1:
                # Linear regression for trend
                x = np.arange(len(counts))
                z = np.polyfit(x, counts, 1)
                slope = z[0]
                
                # Calculate trend direction
                if slope > 0.1:
                    direction = 'increasing'
                elif slope < -0.1:
                    direction = 'decreasing'
                else:
                    direction = 'stable'
                
                # Find last year appeared
                last_year = None
                for i, count in enumerate(reversed(counts)):
                    if count > 0:
                        last_year = years[len(years) - 1 - i]
                        break
                
                trends[topic] = {
                    'slope': slope,
                    'avg_frequency': np.mean(counts),
                    'last_appeared': last_year,
                    'trend_direction': direction,
                    'total_appearances': sum(counts),
                    'years_data': dict(zip(years, counts))
                }
            else:
                trends[topic] = {
                    'slope': 0,
                    'avg_frequency': counts[0] if len(counts) > 0 else 0,
                    'last_appeared': years[0] if len(years) > 0 else None,
                    'trend_direction': 'stable',
                    'total_appearances': counts[0] if len(counts) > 0 else 0,
                    'years_data': dict(zip(years, counts))
                }
        
        self.topic_trends = trends
        return trends
    
    def prepare_features(self, questions_data):
        """Prepare features for ML model"""
        features = []
        labels = []
        
        if not questions_data:
            return np.array([]), np.array([])
        
        df = pd.DataFrame(questions_data)
        
        # Encode categorical variables
        for col in ['topic', 'question_type', 'bloom_level']:
            if col in df.columns:
                le = LabelEncoder()
                # Handle NaN values
                df[col] = df[col].fillna('unknown')
                df[col + '_encoded'] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
        
        # Create features for each question
        for idx, row in df.iterrows():
            feature_vector = []
            
            # Topic encoded
            if 'topic_encoded' in row:
                feature_vector.append(row['topic_encoded'])
            else:
                feature_vector.append(0)
            
            # Question type encoded
            if 'question_type_encoded' in row:
                feature_vector.append(row['question_type_encoded'])
            else:
                feature_vector.append(0)
            
            # Bloom level encoded
            if 'bloom_level_encoded' in row:
                feature_vector.append(row['bloom_level_encoded'])
            else:
                feature_vector.append(0)
            
            # Normalized marks (0-1 scale)
            marks = row.get('marks', 5)
            feature_vector.append(min(marks / 20, 1.0))
            
            # Frequency score
            freq_score = row.get('frequency_score', 1.0)
            feature_vector.append(min(freq_score, 5.0) / 5.0)
            
            # Recency (years since last appearance)
            current_year = datetime.now().year
            year = row.get('year', current_year)
            feature_vector.append(max(0, (current_year - year) / 10))
            
            features.append(feature_vector)
            
            # Label: 1 if similar question appeared next year
            if 'next_year_appeared' in row:
                labels.append(row['next_year_appeared'])
        
        return np.array(features), np.array(labels) if labels else None
    
    def train_model(self, training_data):
        """Train prediction model"""
        if not training_data:
            print("No training data available")
            return False
        
        X, y = self.prepare_features(training_data)
        
        if y is not None and len(y) > 0 and len(X) > 0:
            try:
                # Use Random Forest Classifier for probability prediction
                self.model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
                self.model.fit(X, y)
                print(f"✅ Model trained on {len(X)} samples")
                return True
            except Exception as e:
                print(f"Error training model: {e}")
                return False
        return False
    
    def predict_likely_questions(self, current_questions, historical_trends, year=2026):
        """Predict questions likely to appear in current year"""
        predictions = []
        
        for question in current_questions:
            topic = question.get('topic', 'general')
            question_text = question.get('question_text', '')
            q_type = question.get('question_type', 'unknown')
            marks = question.get('marks', 5)
            
            # Base probability
            probability = 0.5
            
            # Adjust based on historical trends
            if topic in historical_trends:
                trend = historical_trends[topic]
                
                # Higher probability if frequency is high
                probability += min(trend['avg_frequency'] * 0.1, 0.3)
                
                # Adjust based on trend direction
                if trend['trend_direction'] == 'increasing':
                    probability += 0.15
                elif trend['trend_direction'] == 'decreasing':
                    probability -= 0.1
                
                # Less likely if appeared very recently
                if trend['last_appeared'] == year - 1:
                    probability -= 0.2
                elif trend['last_appeared'] == year - 2:
                    probability -= 0.1
                elif trend['last_appeared'] is None:
                    probability += 0.1  # New topic might appear
            
            # Adjust based on question type
            type_weights = {
                'numerical': 0.05,
                'short_answer': 0.02,
                'long_answer': 0.03,
                'mcq': -0.02,
                'diagram': -0.01
            }
            probability += type_weights.get(q_type, 0)
            
            # Adjust based on marks (higher marks questions more important)
            if marks > 10:
                probability += 0.05
            elif marks < 5:
                probability -= 0.02
            
            # Use ML model if available
            if self.model is not None:
                try:
                    # Prepare feature vector for this question
                    features = self._prepare_single_question_features(question)
                    ml_prob = self.model.predict_proba([features])[0][1]
                    # Weighted average (60% ML, 40% rule-based)
                    probability = 0.6 * ml_prob + 0.4 * probability
                except:
                    pass
            
            # Clamp probability between 0 and 1
            probability = max(0, min(1, probability))
            
            # Determine confidence level
            if probability > 0.7:
                confidence = 'High'
            elif probability > 0.4:
                confidence = 'Medium'
            else:
                confidence = 'Low'
            
            predictions.append({
                'question_text': question_text,
                'topic': topic,
                'question_type': q_type,
                'probability': probability,
                'confidence': confidence,
                'suggested_marks': marks
            })
        
        # Sort by probability (highest first)
        predictions.sort(key=lambda x: x['probability'], reverse=True)
        
        return predictions
    
    def _prepare_single_question_features(self, question):
        """Prepare features for a single question for ML prediction"""
        features = []
        
        # Topic encoding
        topic = question.get('topic', 'general')
        if 'topic' in self.label_encoders:
            try:
                encoded = self.label_encoders['topic'].transform([topic])[0]
                features.append(encoded)
            except:
                features.append(0)
        else:
            features.append(0)
        
        # Question type encoding
        q_type = question.get('question_type', 'unknown')
        if 'question_type' in self.label_encoders:
            try:
                encoded = self.label_encoders['question_type'].transform([q_type])[0]
                features.append(encoded)
            except:
                features.append(0)
        else:
            features.append(0)
        
        # Bloom level encoding
        bloom = question.get('bloom_level', 'understand')
        if 'bloom_level' in self.label_encoders:
            try:
                encoded = self.label_encoders['bloom_level'].transform([bloom])[0]
                features.append(encoded)
            except:
                features.append(0)
        else:
            features.append(0)
        
        # Marks
        marks = question.get('marks', 5)
        features.append(min(marks / 20, 1.0))
        
        # Frequency score
        freq_score = question.get('frequency_score', 1.0)
        features.append(min(freq_score, 5.0) / 5.0)
        
        # Recency
        current_year = datetime.now().year
        year = question.get('year', current_year)
        features.append(max(0, (current_year - year) / 10))
        
        return features
    
    def get_topic_summary(self):
        """Get summary of topic trends"""
        if not self.topic_trends:
            return {}
        
        summary = {
            'hot_topics': [],
            'cold_topics': [],
            'emerging_topics': [],
            'stable_topics': []
        }
        
        for topic, trend in self.topic_trends.items():
            if trend['trend_direction'] == 'increasing' and trend['avg_frequency'] > 1:
                summary['hot_topics'].append({
                    'topic': topic,
                    'frequency': trend['avg_frequency'],
                    'trend': trend['slope']
                })
            elif trend['trend_direction'] == 'decreasing':
                summary['cold_topics'].append({
                    'topic': topic,
                    'frequency': trend['avg_frequency']
                })
            elif trend['last_appeared'] is None or trend['last_appeared'] < datetime.now().year - 2:
                summary['emerging_topics'].append({
                    'topic': topic,
                    'last_appeared': trend['last_appeared']
                })
            else:
                summary['stable_topics'].append({
                    'topic': topic,
                    'frequency': trend['avg_frequency']
                })
        
        # Sort by frequency
        summary['hot_topics'].sort(key=lambda x: x['frequency'], reverse=True)
        summary['hot_topics'] = summary['hot_topics'][:5]  # Top 5 hot topics
        
        return summary
    
    def save_model(self, path='models/'):
        """Save trained model"""
        if not os.path.exists(path):
            os.makedirs(path)
        
        if self.model:
            try:
                joblib.dump(self.model, os.path.join(path, 'predictor_model.pkl'))
                print(f"✅ Model saved to {path}")
            except Exception as e:
                print(f"Error saving model: {e}")
        
        if self.label_encoders:
            try:
                joblib.dump(self.label_encoders, os.path.join(path, 'label_encoders.pkl'))
                print(f"✅ Label encoders saved to {path}")
            except Exception as e:
                print(f"Error saving label encoders: {e}")
        
        if self.topic_trends:
            try:
                with open(os.path.join(path, 'topic_trends.json'), 'w') as f:
                    json.dump(self.topic_trends, f, indent=2)
                print(f"✅ Topic trends saved to {path}")
            except Exception as e:
                print(f"Error saving topic trends: {e}")
    
    def load_model(self, path='models/'):
        """Load trained model"""
        model_path = os.path.join(path, 'predictor_model.pkl')
        encoders_path = os.path.join(path, 'label_encoders.pkl')
        trends_path = os.path.join(path, 'topic_trends.json')
        
        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                print(f"✅ Model loaded from {model_path}")
            except Exception as e:
                print(f"Error loading model: {e}")
        
        if os.path.exists(encoders_path):
            try:
                self.label_encoders = joblib.load(encoders_path)
                print(f"✅ Label encoders loaded from {encoders_path}")
            except Exception as e:
                print(f"Error loading label encoders: {e}")
        
        if os.path.exists(trends_path):
            try:
                with open(trends_path, 'r') as f:
                    self.topic_trends = json.load(f)
                print(f"✅ Topic trends loaded from {trends_path}")
            except Exception as e:
                print(f"Error loading topic trends: {e}")


# Simple function-based interface for backward compatibility
def analyze_historical_data(questions_data):
    """Simple function to analyze historical data"""
    predictor = QuestionPredictor()
    return predictor.analyze_historical_data(questions_data)

def predict_likely_questions(current_questions, historical_trends, year=2026):
    """Simple function to predict likely questions"""
    predictor = QuestionPredictor()
    return predictor.predict_likely_questions(current_questions, historical_trends, year)


# Test the module
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Question Predictor")
    print("=" * 60)
    
    # Sample historical data
    sample_data = [
        {'topic': 'algorithms', 'year': 2022, 'question_text': 'What is sorting?', 'question_type': 'short_answer', 'marks': 5, 'frequency_score': 1.0},
        {'topic': 'algorithms', 'year': 2023, 'question_text': 'Explain bubble sort', 'question_type': 'long_answer', 'marks': 10, 'frequency_score': 1.2},
        {'topic': 'algorithms', 'year': 2024, 'question_text': 'Compare sorting algorithms', 'question_type': 'long_answer', 'marks': 10, 'frequency_score': 1.3},
        {'topic': 'databases', 'year': 2022, 'question_text': 'What is SQL?', 'question_type': 'short_answer', 'marks': 5, 'frequency_score': 1.0},
        {'topic': 'databases', 'year': 2023, 'question_text': 'Explain joins', 'question_type': 'long_answer', 'marks': 10, 'frequency_score': 1.1},
    ]
    
    # Initialize predictor
    predictor = QuestionPredictor()
    print("✅ QuestionPredictor initialized")
    
    # Analyze trends
    trends = predictor.analyze_historical_data(sample_data)
    print(f"\n✅ Analyzed {len(trends)} topics")
    
    # Get current questions
    current_questions = [
        {'topic': 'algorithms', 'question_text': 'What is quicksort?', 'question_type': 'long_answer', 'marks': 10},
        {'topic': 'databases', 'question_text': 'What is normalization?', 'question_type': 'short_answer', 'marks': 5},
    ]
    
    # Make predictions
    predictions = predictor.predict_likely_questions(current_questions, trends, year=2026)
    
    print("\nPredictions for 2026:")
    print("-" * 40)
    for i, pred in enumerate(predictions, 1):
        print(f"\n{i}. {pred['question_text']}")
        print(f"   Topic: {pred['topic']}")
        print(f"   Probability: {pred['probability']:.1%}")
        print(f"   Confidence: {pred['confidence']}")
    
    # Get topic summary
    summary = predictor.get_topic_summary()
    print("\n" + "=" * 60)
    print("Topic Summary:")
    print("-" * 40)
    if summary.get('hot_topics'):
        print(f"🔥 Hot Topics: {[t['topic'] for t in summary['hot_topics']]}")
    if summary.get('cold_topics'):
        print(f"❄️ Cold Topics: {[t['topic'] for t in summary['cold_topics'][:3]]}")
    
    print("\n✅ Test complete!")