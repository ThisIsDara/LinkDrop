function viewLog(linkId) {
    fetch(`/admin/log/${linkId}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('logContent').textContent = data.log;
            document.getElementById('logModal').classList.add('show');
        })
        .catch(error => {
            console.error('Error fetching log:', error);
            alert('Failed to load log');
        });
}

function closeLog() {
    document.getElementById('logModal').classList.remove('show');
}

function openPathModal(linkId, currentPath) {
    document.getElementById('pathForm').action = `/admin/set_path/${linkId}`;
    document.getElementById('downloadPath').value = currentPath || '';
    document.getElementById('pathModal').classList.add('show');
}

function closePathModal() {
    document.getElementById('pathModal').classList.remove('show');
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeLog();
        closePathModal();
    }
});

document.getElementById('logModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeLog();
    }
});

document.getElementById('pathModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closePathModal();
    }
});