// Mobile menu functionality
function toggleMobileMenu() {
    const mobileMenu = document.getElementById('mobile-menu');
    if (mobileMenu) {
        mobileMenu.classList.toggle('hidden');
    }
}

// Mobile dropdown functionality  
function toggleMobileDropdown() {
    const dropdown = document.getElementById('mobile-dropdown');
    const icon = document.getElementById('mobile-dropdown-icon');
    if (dropdown && icon) {
        dropdown.classList.toggle('hidden');
        icon.classList.toggle('rotate-180');
    }
}

// Navbar scroll effect
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('nav');
    if (window.scrollY > 100) {
        navbar.classList.add('shadow-lg');
    } else {
        navbar.classList.remove('shadow-lg');
    }
});

// Intersection Observer for animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-fade-in-up');
        }
    });
}, observerOptions);

// Initialize observers when page loads
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.hover-lift, .service-card').forEach(el => {
        observer.observe(el);
    });
});
