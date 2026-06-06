/**
 * Memo Template Renderer
 * Dynamically renders memo pages using templates and data files
 */

class MemoRenderer {
  constructor(config) {
    this.config = config;
    this.container = document.getElementById('memo-content');
  }

  async render() {
    if (!this.container) {
      console.error('Memo content container not found');
      return;
    }

    try {
      // Load data
      const data = await this.loadData(this.config.dataFile);

      // Render based on table type
      if (data.tableType === 'bootstrap') {
        this.renderBootstrapTable(data);
      } else if (data.tableType === 'custom') {
        this.renderCustomTable(data);
      }

      // Update page metadata
      this.updateMetadata(data);
    } catch (error) {
      console.error('Error rendering memo:', error);
    }
  }

  async loadData(dataFile) {
    const response = await fetch(dataFile);
    if (!response.ok) {
      throw new Error(`Failed to load data: ${response.statusText}`);
    }
    return await response.json();
  }

  renderBootstrapTable(data) {
    const html = `
      <header class="post-header">
        <h1 class="post-title">${data.title}</h1>
        ${data.subtitle ? `<p class="post-description">${data.subtitle}</p>` : ''}
      </header>
      <article>
        <div class="news">
          <div class="table-responsive" style="max-height: 60vw">
            <table class="table table-sm table-borderless">
              ${data.items.map(item => `
                <tr>
                  <th scope="row" style="width: 20%;font-family: monospace;"> ${item.date}</th>
                  <td> <a href="${item.url}">${item.title}</a> </td>
                </tr>
              `).join('')}
            </table>
          </div>
        </div>
      </article>
    `;
    this.container.innerHTML = html;
  }

  renderCustomTable(data) {
    const html = `
      <header class="post-header">
        <h1 class="post-title">${data.title}</h1>
        ${data.subtitle ? `<p class="post-description">${data.subtitle}</p>` : ''}
      </header>
      <article>
        <table class="${data.tableClass || 'paper-table'}">
          <thead>
            <tr>
              ${data.columns.map(col => `<th>${col}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${data.items.map(item => `
              <tr>
                ${item.values.map((val, idx) => `
                  <td class="${data.columnClasses ? data.columnClasses[idx] : ''}">
                    ${item.values.length === idx + 1 && item.url ?
                      `<a href="${item.url}">${val}</a>` : val}
                  </td>
                `).join('')}
              </tr>
            `).join('')}
          </tbody>
        </table>
      </article>
    `;
    this.container.innerHTML = html;
  }

  updateMetadata(data) {
    // Update title
    document.title = data.title;

    // Update meta tags
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription && data.description) {
      metaDescription.setAttribute('content', data.description);
    }

    const metaKeywords = document.querySelector('meta[name="keywords"]');
    if (metaKeywords && data.keywords) {
      metaKeywords.setAttribute('content', data.keywords);
    }

    // Update canonical
    const canonical = document.querySelector('link[rel="canonical"]');
    if (canonical && data.url) {
      canonical.setAttribute('href', `https://pengandy.com/${data.url}`);
    }

    // Update body data-page attribute
    if (data.pageId) {
      document.body.setAttribute('data-page', data.pageId);
    }
  }
}

// Auto-initialize if config is provided
document.addEventListener('DOMContentLoaded', () => {
  if (window.memoConfig) {
    const renderer = new MemoRenderer(window.memoConfig);
    renderer.render();
  }
});
