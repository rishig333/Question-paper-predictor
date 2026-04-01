# run.py - Flask version
import subprocess
import sys
import webbrowser
import time
import os

def main():
    """Run the Flask application"""
    print("=" * 60)
    print("🚀 Question Paper Predictor - Flask Edition")
    print("=" * 60)
    
    # Check if required files exist
    required_files = ['app_flask.py', 'database.py', 'ocr_processor.py', 
                      'question_analyzer.py', 'predictor.py']
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nPlease make sure all project files are present.")
        return
    
    # Check if templates folder exists
    if not os.path.exists('templates'):
        print("❌ Templates folder not found!")
        print("Please create a 'templates' folder with HTML files.")
        return
    
    # Check if static folder exists
    if not os.path.exists('static'):
        print("⚠️ Static folder not found. Creating...")
        os.makedirs('static/css', exist_ok=True)
        os.makedirs('static/js', exist_ok=True)
        os.makedirs('static/img', exist_ok=True)
    
    # Create uploads folder if it doesn't exist
    os.makedirs('uploads', exist_ok=True)
    
    print("\n📁 Project structure verified!")
    print("📊 Starting Flask server...")
    print("🌐 Opening browser in 3 seconds...")
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(3)
        webbrowser.open('http://localhost:5000')
        print("✅ Browser opened! If not, go to: http://localhost:5000")
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run Flask app
    try:
        from app_flask import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nTrying alternative method...")
        
        # Alternative: run with flask command
        os.environ['FLASK_APP'] = 'app_flask.py'
        os.environ['FLASK_ENV'] = 'development'
        os.environ['FLASK_DEBUG'] = '1'
        
        subprocess.run([sys.executable, '-m', 'flask', 'run', '--host=0.0.0.0', '--port=5000'])
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()