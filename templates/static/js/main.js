// Question Paper Predictor - Main JavaScript

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Question Paper Predictor Loaded');
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add fade-in animation to main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }
});

// Utility Functions
const Utils = {
    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // Show notification
    showNotification: function(message, type = 'success') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
        }
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 300);
        }, 5000);
    },
    
    // Debounce function for search
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// File Upload Handling
class FileUploadHandler {
    constructor(dropAreaId, fileInputId, fileListId) {
        this.dropArea = document.getElementById(dropAreaId);
        this.fileInput = document.getElementById(fileInputId);
        this.fileList = document.getElementById(fileListId);
        this.selectedFiles = [];
        
        this.init();
    }
    
    init() {
        if (!this.dropArea) return;
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropArea.addEventListener(eventName, this.preventDefaults.bind(this), false);
            document.body.addEventListener(eventName, this.preventDefaults.bind(this), false);
        });
        
        // Highlight drop area on drag over
        ['dragenter', 'dragover'].forEach(eventName => {
            this.dropArea.addEventListener(eventName, this.highlight.bind(this), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            this.dropArea.addEventListener(eventName, this.unhighlight.bind(this), false);
        });
        
        // Handle dropped files
        this.dropArea.addEventListener('drop', this.handleDrop.bind(this), false);
        
        // Handle file input change
        if (this.fileInput) {
            this.fileInput.addEventListener('change', this.handleFiles.bind(this));
        }
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    highlight() {
        this.dropArea.classList.add('dragover');
    }
    
    unhighlight() {
        this.dropArea.classList.remove('dragover');
    }
    
    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        this.handleFiles({ target: { files: files } });
    }
    
    handleFiles(e) {
        this.selectedFiles = [...e.target.files];
        this.updateFileList();
        
        // Enable submit button if files selected
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            submitBtn.disabled = this.selectedFiles.length === 0;
        }
    }
    
    updateFileList() {
        if (!this.fileList) return;
        
        this.fileList.innerHTML = '';
        this.selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <i class="fas fa-file-pdf text-danger"></i>
                        <strong>${file.name}</strong>
                        <small class="text-muted ms-2">(${Utils.formatFileSize(file.size)})</small>
                    </div>
                    <button type="button" class="btn btn-sm btn-danger" onclick="window.removeFile(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            this.fileList.appendChild(fileItem);
        });
    }
    
    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updateFileList();
        
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            submitBtn.disabled = this.selectedFiles.length === 0;
        }
    }
}

// Make removeFile globally accessible
window.removeFile = function(index) {
    if (window.fileUploadHandler) {
        window.fileUploadHandler.removeFile(index);
    }
};

// Initialize file upload handler when page loads
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('dropArea')) {
        window.fileUploadHandler = new FileUploadHandler('dropArea', 'fileInput', 'fileList');
    }
});