// Smart Notes Summarizer Client Logic

// Sample study materials for quick demonstration
const sampleNotes = {
    networks: `The Open Systems Interconnection (OSI) model describes seven layers that computer systems use to communicate over a network. It was the first standard model for network communications, adopted by all major computer and telecommunication companies in the early 1980s. The seven layers are Physical, Data Link, Network, Transport, Session, Presentation, and Application. The Physical layer transmits raw bit streams over physical cable. The Data Link layer defines the format of data on the network. The Network layer decides which physical path the data will take. The Transport layer transmits data using transmission protocols including TCP and UDP. The modern Internet is not based on OSI, but on the simpler TCP/IP model. However, the OSI 7-layer model is still widely used, as it helps visualize and communicate how networks operate.`,
    
    os: `A deadlock in operating systems is a situation where a set of processes are blocked because each process is holding a resource and waiting for another resource acquired by some other process. Four conditions must hold simultaneously for a deadlock to occur: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait. Mutual exclusion means only one process can use a resource at any given time. Hold and wait occurs when a process is holding at least one resource and waiting to acquire additional resources. No preemption means resources cannot be forcibly confiscated from a process holding them. Circular wait means a set of processes are waiting for resources in a circular chain. Operating systems handle deadlocks using deadlock prevention, deadlock avoidance algorithms like Banker's Algorithm, deadlock detection and recovery, or ignorance through the Ostrich algorithm.`,
    
    ml: `Overfitting is an undesirable machine learning behavior that occurs when the machine learning model gives accurate predictions for training data but fails to generalize well to unseen test data. When a model trains for too long on sample data or when the model is too complex, it learns the "noise" or irrelevant information within the dataset along with the underlying relationships. Overfitting happens when a model fits the data too well. Key signs of overfitting include very low error on the training dataset but high error on validation or test datasets. Common techniques to prevent overfitting include cross-validation, regularization such as L1 and L2 penalties, data augmentation, early stopping during model training, reducing model complexity, and ensembling multiple models like Random Forests.`
};

document.addEventListener('DOMContentLoaded', () => {
    // Word & Character Counter
    const textarea = document.querySelector('textarea.editor');
    const wordCountEl = document.getElementById('val-words');
    const charCountEl = document.getElementById('val-chars');
    const readTimeEl = document.getElementById('val-time');

    function updateStats() {
        if (!textarea) return;
        const text = textarea.value.trim();
        const chars = textarea.value.length;
        const words = text === '' ? 0 : text.split(/\s+/).filter(Boolean).length;
        const readTime = Math.max(1, Math.ceil(words / 200));

        if (wordCountEl) wordCountEl.textContent = words;
        if (charCountEl) charCountEl.textContent = chars;
        if (readTimeEl) readTimeEl.textContent = `${readTime} min`;
    }

    if (textarea) {
        textarea.addEventListener('input', updateStats);
        updateStats();
    }

    // Quick Sample Buttons
    const sampleChips = document.querySelectorAll('.sample-chip');
    sampleChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const key = chip.dataset.sample;
            if (sampleNotes[key] && textarea) {
                textarea.value = sampleNotes[key];
                updateStats();
                textarea.focus();
                showToast(`Loaded sample: ${chip.textContent.trim()}`);
            }
        });
    });

    // Form submission loading state
    const summarizeForm = document.getElementById('summarize-form');
    const summarizeBtn = document.getElementById('summarize-btn');
    if (summarizeForm && summarizeBtn) {
        summarizeForm.addEventListener('submit', (e) => {
            if (!textarea.value.trim()) {
                e.preventDefault();
                showToast('Please enter some study material first.');
                textarea.focus();
                return;
            }
            summarizeBtn.disabled = true;
            summarizeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating Summary...';
        });
    }

    // Setup Copy Buttons
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            const targetEl = document.getElementById(targetId);
            if (!targetEl) return;

            const textToCopy = targetEl.innerText || targetEl.textContent;
            navigator.clipboard.writeText(textToCopy.trim()).then(() => {
                const originalHtml = btn.innerHTML;
                btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                btn.style.color = 'var(--success)';
                btn.style.borderColor = 'var(--success)';
                showToast('Copied to clipboard!');

                setTimeout(() => {
                    btn.innerHTML = originalHtml;
                    btn.style.color = '';
                    btn.style.borderColor = '';
                }, 2000);
            }).catch(() => {
                showToast('Failed to copy to clipboard.');
            });
        });
    });
});

// Toast notification helper
function showToast(message) {
    let toast = document.querySelector('.toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.innerHTML = `<i class="fa-solid fa-circle-check" style="color: #10b981;"></i> <span>${message}</span>`;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
