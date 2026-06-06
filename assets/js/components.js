/**
 * Component Loader
 * Dynamically loads navbar and footer components into pages
 */

(function() {
  'use strict';

  /**
   * Load a component HTML file and insert it into the target element
   */
  function loadComponent(url, targetSelector) {
    return fetch(url)
      .then(response => {
        if (!response.ok) {
          throw new Error(`Failed to load ${url}: ${response.statusText}`);
        }
        return response.text();
      })
      .then(html => {
        const target = document.querySelector(targetSelector);
        if (target) {
          target.innerHTML = html;
          
          // Execute any scripts in the loaded HTML
          const scripts = target.querySelectorAll('script');
          scripts.forEach(script => {
            const newScript = document.createElement('script');
            if (script.src) {
              newScript.src = script.src;
            } else {
              newScript.textContent = script.textContent;
            }
            document.body.appendChild(newScript);
          });
        } else {
          console.warn(`Target element ${targetSelector} not found`);
        }
      })
      .catch(error => {
        console.error('Error loading component:', error);
      });
  }

  /**
   * Initialize component loading when DOM is ready
   */
  function initComponents() {
    const promises = [];
    
    // Cache busting parameter to force reload of components
    const cacheBuster = '?v=' + Date.now();
    
    // Load navbar if placeholder exists
    if (document.getElementById('navbar-placeholder')) {
      promises.push(loadComponent('/components/navbar.html' + cacheBuster, '#navbar-placeholder'));
    }
    
    // Load footer if placeholder exists
    if (document.getElementById('footer-placeholder')) {
      promises.push(loadComponent('/components/footer.html' + cacheBuster, '#footer-placeholder'));
    }

    // Run progress bar setup and set active nav after navbar is loaded
    Promise.all(promises).then(() => {
      // Set active nav item based on current page
      const currentPage = document.body.getAttribute('data-page');
      if (currentPage) {
        const navItem = document.querySelector(`.navbar-nav [data-page="${currentPage}"]`);
        if (navItem) {
          navItem.classList.add('active');
          const link = navItem.querySelector('.nav-link');
          if (link) {
            link.innerHTML += '<span class="sr-only">(current)</span>';
          }
        }
      }
      
      if (typeof progressBarSetup === 'function') {
        progressBarSetup();
      }
    });
  }

  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initComponents);
  } else {
    initComponents();
  }
})();

