// public/js/script.js
let currentUser = null;

function showMessage(msg, type = 'info') {
    const el = document.getElementById('message');
    if (el) {
        el.textContent = msg;
        el.style.color = type === 'success' ? 'green' : 'red';
    }
}

async function apiCall(url, options = {}) {
    const res = await fetch(url, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...options.headers }
    });
    return res.json();
}

// Register
document.getElementById('registerForm')?.addEventListener('submit', async e => {
    e.preventDefault();
    const data = new FormData(e.target);
    const res = await fetch('/register', { method: 'POST', body: data });
    const out = await res.json();
    showMessage(out.message, out.success ? 'success' : 'error');
    if (out.success) setTimeout(() => location.href = '/login.html', 1500);
});

// Login
document.getElementById('loginForm')?.addEventListener('submit', async e => {
    e.preventDefault();
    const data = new FormData(e.target);
    const res = await fetch('/login', { method: 'POST', body: data });
    const out = await res.json();
    showMessage(out.message, out.success ? 'success' : 'error');
    if (out.success) {
        currentUser = { id: out.user_id, role: out.role };
        localStorage.setItem('user', JSON.stringify(currentUser));
        setTimeout(() => location.href = '/', 1000);
    }
});

// Load Jobs
async function loadJobs() {
    const jobs = await apiCall('/api/jobs');
    const container = document.getElementById('jobList');
    if (container) {
        container.innerHTML = jobs.map(j => `
            <div class="job-card">
                <h3>${j.title}</h3>
                <p>${j.description}</p>
                <p>${j.location} | $${j.salary} | ${j.category}</p>
                ${currentUser?.role === 'seeker' ? `<button onclick="apply(${j.job_id})">Apply</button>` : ''}
            </div>
        `).join('');
    }
}

// Apply
window.apply = async (job_id) => {
    const res = await apiCall(`/apply/${job_id}`, { method: 'POST' });
    showMessage(res.message, res.success ? 'success' : 'error');
};

// Load My Jobs
async function loadMyJobs() {
    const jobs = await apiCall('/employer/my_jobs');
    const container = document.getElementById('myJobsList');
    if (container) {
        container.innerHTML = jobs.map(j => `
            <div class="job-card">
                <h3>${j.title}</h3>
                <p>${j.description}</p>
                <button onclick="location.href='edit_job.html?id=${j.job_id}'">Edit</button>
            </div>
        `).join('');
    }
}

// Load My Applications
async function loadMyApplications() {
    const apps = await apiCall('/my_applications');
    const container = document.getElementById('myApplicationsList');
    if (container) {
        container.innerHTML = apps.map(a => `
            <div class="app-card">
                <p>Job: ${a.title}</p>
                <p>Status: ${a.status}</p>
            </div>
        `).join('');
    }
}

// Post Job
document.getElementById('postJobForm')?.addEventListener('submit', async e => {
    e.preventDefault();
    const data = new FormData(e.target);
    const res = await fetch('/employer/post_job', { method: 'POST', body: data });
    const out = await res.json();
    showMessage(out.message, out.success ? 'success' : 'error');
    if (out.success) {
        e.target.reset();
        loadMyJobs();
    }
});

// On page load
document.addEventListener('DOMContentLoaded', () => {
    const saved = localStorage.getItem('user');
    if (saved) currentUser = JSON.parse(saved);

    loadJobs();
    if (location.pathname.includes('employer_jobs')) loadMyJobs();
    if (location.pathname.includes('my_applications')) loadMyApplications();
});