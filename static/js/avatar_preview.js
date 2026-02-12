// Avatar Preview/Zoom functionality
document.addEventListener('DOMContentLoaded', function () {
    // Add modal HTML to page if not exists
    if (!document.getElementById('avatarPreviewModal')) {
        const modalHTML = `
        <div id="avatarPreviewModal" 
            style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 2000; align-items: center; justify-content: center; cursor: pointer;"
            onclick="closeAvatarPreview()">
            <div style="position: relative; max-width: 90%; max-height: 90vh;">
                <img id="avatarPreviewImage" src="" style="max-width:  100%; max-height: 90vh; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.5); display: none;">
                <div id="avatarPreviewEmoji" style="width: 400px; height: 400px; background: #2a2a2a; display: none; align-items: center; justify-content: center; font-size: 15rem; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.5);"></div>
                <button onclick="closeAvatarPreview(); event.stopPropagation();" 
                    style="position: absolute; top: -40px; right: 0; background: rgba(255,255,255,0.1); border: none; color: white; font-size: 2rem; width: 40px; height: 40px; border-radius: 50%; cursor: pointer;">×</button>
            </div>
        </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    // Add click handler to navbar avatar
    const navAvatar = document.querySelector('.nav-avatar');
    if (navAvatar) {
        navAvatar.style.cursor = 'pointer';
        navAvatar.style.transition = 'transform 0.2s';
        navAvatar.addEventListener('click', openAvatarPreview);
        navAvatar.addEventListener('mouseover', () => navAvatar.style.transform = 'scale(1.1)');
        navAvatar.addEventListener('mouseout', () => navAvatar.style.transform = 'scale(1)');
    }
});

window.openAvatarPreview = function () {
    const modal = document.getElementById('avatarPreviewModal');
    if (!modal) return;

    const previewImg = document.getElementById('avatarPreviewImage');
    const previewEmoji = document.getElementById('avatarPreviewEmoji');

    // Get avatar data from nav-avatar or settings avatar  
    const navAvatar = document.querySelector('.nav-avatar img');
    const settingsAvatar = document.getElementById('settingsAvatar');

    if (navAvatar || (settingsAvatar && settingsAvatar.tagName === 'IMG')) {
        // Upload type avatar
        const imgSrc = navAvatar ? navAvatar.src : settingsAvatar.src;
        previewImg.src = imgSrc;
        previewImg.style.display = 'block';
        previewEmoji.style.display = 'none';
    } else {
        // Emoji type avatar
        const emojiText = settingsAvatar ? settingsAvatar.textContent.trim() : (document.querySelector('.nav-avatar').textContent.trim() || '👤');
        previewEmoji.textContent = emojiText;
        previewEmoji.style.display = 'flex';
        previewImg.style.display = 'none';
    }

    modal.style.display = 'flex';
};

window.closeAvatarPreview = function () {
    const modal = document.getElementById('avatarPreviewModal');
    if (modal) modal.style.display = 'none';
};
