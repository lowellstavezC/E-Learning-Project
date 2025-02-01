// Material upload handling
document.addEventListener('DOMContentLoaded', function() {
    const materialForm = document.getElementById('material-upload-form');
    if (materialForm) {
        materialForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Material uploaded successfully!', 'success');
                    materialForm.reset();
                }
            })
            .catch(error => {
                showNotification('Error uploading material', 'error');
            });
        });
    }

    // File preview functionality
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            previewFile(this);
        });
    }
});

// Utility functions
function previewFile(input) {
    const preview = document.getElementById('file-preview');
    if (preview && input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onloadend = function () {
            preview.src = reader.result;
        }
        reader.readAsDataURL(input.files[0]);
    }
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg text-white ${
        type === 'success' ? 'bg-green-500' : 'bg-red-500'
    }`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
