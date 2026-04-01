# ocr_processor.py - Updated to accept use_easyocr parameter
import os
import re
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import pdf2image

class OCRProcessor:
    """OCR Processor using Pillow and Tesseract"""
    
    def __init__(self, use_easyocr=False, tesseract_path=None):
        """
        Initialize OCR Processor
        
        Args:
            use_easyocr: (bool) Whether to use EasyOCR (ignored, kept for compatibility)
            tesseract_path: (str) Path to tesseract executable
        """
        # Configure Tesseract path
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        elif os.name == 'nt':
            possible_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"✅ Tesseract found at: {path}")
                    break
            else:
                print("⚠️ Tesseract not found. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
    
    def preprocess_image(self, image):
        """Enhance image using Pillow"""
        if image.mode != 'L':
            image = image.convert('L')
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        return image
    
    def extract_text_from_image(self, image_path):
        """Extract text from image"""
        try:
            image = Image.open(image_path)
            processed = self.preprocess_image(image)
            text = pytesseract.image_to_string(processed, lang='eng')
            return self._clean_text(text)
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def extract_text_from_pdf(self, pdf_path, dpi=150):
        """Extract text from PDF"""
        try:
            images = pdf2image.convert_from_path(pdf_path, dpi=dpi)
            full_text = ""
            for i, image in enumerate(images):
                processed = self.preprocess_image(image)
                text = pytesseract.image_to_string(processed, lang='eng')
                full_text += f"\n--- Page {i+1} ---\n{text}\n"
            return self._clean_text(full_text)
        except Exception as e:
            print(f"PDF Error: {e}")
            return ""
    
    def extract_text(self, file_path):
        """Extract text from file"""
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            return self.extract_text_from_image(file_path)
        elif ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        else:
            return f"Unsupported format: {ext}"
    
    def _clean_text(self, text):
        """Clean extracted text"""
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()