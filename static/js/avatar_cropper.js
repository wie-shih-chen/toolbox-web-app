// Avatar Cropping with Cropper.js
let cropper = null;

// Handle file selection
window.handleAvatarFileSelect = function (event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (e) {
        const cropImage = document.getElementById('cropImage');
        const selectionView = document.getElementById('avatarSelectionView');
        const cropView = document.getElementById('avatarCropView');

        if (!cropImage || !selectionView || !cropView) {
            console.error('Required elements not found');
            return;
        }

        cropImage.src = e.target.result;

        // Hide selection view, show crop view
        selectionView.style.display = 'none';
        cropView.style.display = 'block';

        // Destroy existing cropper if any
        if (cropper) {
            cropper.destroy();
        }

        // Wait for image to load
        cropImage.onload = function () {
            // Initialize Cropper.js with circular crop
            cropper = new Cropper(cropImage, {
                aspectRatio: 1,
                viewMode: 1,
                dragMode: 'move',
                autoCropArea: 0.9,
                restore: false,
                guides: true,
                center: true,
                highlight: false,
                cropBoxMovable: true,
                cropBoxResizable: true,
                toggleDragModeOnDblclick: false,
                minCropBoxWidth: 200,
                minCropBoxHeight: 200
            });

            // Apply circular mask using CSS
            setTimeout(() => {
                const cropBox = document.querySelector('.cropper-crop-box');
                const face = document.querySelector('.cropper-face');
                if (cropBox && face) {
                    cropBox.style.borderRadius = '50%';
                    face.style.borderRadius = '50%';
                }
            }, 100);
        };
    };
    reader.readAsDataURL(file);
};

// Cancel cropping
window.cancelCrop = function () {
    const selectionView = document.getElementById('avatarSelectionView');
    const cropView = document.getElementById('avatarCropView');
    const fileInput = document.getElementById('avatarFileInput');

    // Show selection view, hide crop view
    if (selectionView) selectionView.style.display = 'block';
    if (cropView) cropView.style.display = 'none';
    if (fileInput) fileInput.value = '';

    if (cropper) {
        cropper.destroy();
        cropper = null;
    }
};

// Confirm crop and upload
window.confirmCrop = async function () {
    if (!cropper) {
        alert('請先選擇圖片');
        return;
    }

    // Get cropped canvas
    const canvas = cropper.getCroppedCanvas({
        width: 400,
        height: 400,
        imageSmoothingEnabled: true,
        imageSmoothingQuality: 'high'
    });

    if (!canvas) {
        alert('裁切失敗，請重試');
        return;
    }

    // Show loading state
    const confirmBtn = event.target;
    const originalText = confirmBtn.textContent;
    confirmBtn.textContent = '上傳中...';
    confirmBtn.disabled = true;

    // Convert canvas to blob
    canvas.toBlob(async function (blob) {
        if (!blob) {
            alert('圖片處理失敗');
            confirmBtn.textContent = originalText;
            confirmBtn.disabled = false;
            return;
        }

        // Create form data
        const formData = new FormData();
        formData.append('avatar_file', blob, 'avatar.png');

        // Upload via fetch
        try {
            const response = await fetch('/auth/avatar/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                // Success - reload page to show new avatar
                window.location.reload();
            } else {
                const data = await response.json();
                alert(data.error || '上傳失敗，請重試');
                confirmBtn.textContent = originalText;
                confirmBtn.disabled = false;
            }
        } catch (error) {
            console.error('Upload error:', error);
            alert('上傳失敗，請檢查網路連線');
            confirmBtn.textContent = originalText;
            confirmBtn.disabled = false;
        }
    }, 'image/png', 0.95);
};

// Add styles for circular cropper
document.addEventListener('DOMContentLoaded', function () {
    // Inject custom styles for circular crop box
    const style = document.createElement('style');
    style.textContent = `
        .cropper-view-box,
        .cropper-face {
            border-radius: 50%;
        }
        
        .cropper-crop-box {
            border-radius: 50%;
        }
        
        .cropper-view-box {
            outline: 0;
            box-shadow: 0 0 0 1px #39f;
        }
    `;
    document.head.appendChild(style);
});
