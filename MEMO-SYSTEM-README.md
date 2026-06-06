# Memo Template System

A JavaScript-based dynamic rendering system for creating memo pages with reusable templates.

## Architecture

### Files Structure
```
/
├── memo-template.html          # Template file for creating new memo pages
├── LPmemo.html                 # Example: Leadership memo (uses bootstrap table)
├── papermemo.html              # Example: Papers memo (uses custom table)
├── /assets/js/
│   └── memo-renderer.js        # Template rendering engine
└── /data/
    ├── LPmemo-data.json        # Data file for LPmemo
    └── papermemo-data.json     # Data file for papermemo
```

## How It Works

1. **HTML Shell** (e.g., `LPmemo.html`): Minimal HTML file that loads the renderer
2. **Data File** (e.g., `/data/LPmemo-data.json`): JSON file containing all content
3. **Renderer** (`memo-renderer.js`): JavaScript that combines template + data

## Creating a New Memo Page

### Step 1: Create a Data File

Create `/data/yourmemo-data.json`:

**For Bootstrap 2-column table (like LPmemo):**
```json
{
  "title": "Your Memo Title",
  "subtitle": "Optional subtitle",
  "description": "SEO description",
  "keywords": "keyword1, keyword2",
  "url": "yourmemo",
  "pageId": "yourmemo",
  "tableType": "bootstrap",
  "items": [
    {
      "date": "December, 2025",
      "title": "Link text",
      "url": "https://example.com"
    }
  ]
}
```

**For Custom 3-column table (like papermemo):**
```json
{
  "title": "Your Memo Title",
  "subtitle": "Optional subtitle",
  "description": "SEO description",
  "keywords": "keyword1, keyword2",
  "url": "yourmemo",
  "pageId": "yourmemo",
  "tableType": "custom",
  "tableClass": "paper-table",
  "columns": ["Column 1", "Column 2", "Column 3"],
  "columnClasses": ["year-col", "title-col", "venue-col"],
  "items": [
    {
      "values": ["2025", "Title here", "Venue here"],
      "url": "https://example.com"
    }
  ]
}
```

### Step 2: Create HTML Page

Copy `memo-template.html` to `yourmemo.html` and update:

```html
<title>Your Memo Title</title>
<meta name="description" content="Your description">
<meta name="keywords" content="Your, Keywords">
<link rel="canonical" href="https://pengandy.com/yourmemo">

<script>
   window.memoConfig = {
      dataFile: '/data/yourmemo-data.json'  // Update this path
   };
</script>

<body data-page="yourmemo">
```

### Step 3: Add Custom Styles (Optional)

If using `tableType: "custom"`, add CSS styles to the HTML page:

```html
<style>
   .your-table-class {
      /* Your custom styles */
   }
</style>
```

## Editing Existing Memos

To update a memo page:
1. Edit the JSON file in `/data/` (e.g., `/data/LPmemo-data.json`)
2. No need to touch the HTML file

## Benefits

✅ **Separation of Concerns**: Content (JSON) separate from presentation (HTML/JS)
✅ **Reusable Template**: One template supports multiple table types
✅ **Easy Updates**: Edit JSON files without touching HTML structure
✅ **Consistent Styling**: All memos use the same rendering engine
✅ **Type Flexibility**: Supports both Bootstrap and custom table structures

## Examples

- **LPmemo.html**: Leadership memo using Bootstrap 2-column table
  - Data: `/data/LPmemo-data.json`
  - Style: Bootstrap table (borderless, responsive)

- **papermemo.html**: Papers memo using custom 3-column table
  - Data: `/data/papermemo-data.json`
  - Style: Custom `.paper-table` CSS

## Migration Guide

To migrate an existing static memo page:

1. Extract data from HTML into JSON format
2. Create data file in `/data/`
3. Copy `memo-template.html` to create new HTML shell
4. Update `memoConfig.dataFile` to point to your data file
5. Test the page
6. Remove old static content from HTML

## Renderer API

The `MemoRenderer` class provides:

- `renderBootstrapTable(data)`: Renders 2-column Bootstrap table
- `renderCustomTable(data)`: Renders custom multi-column table
- `updateMetadata(data)`: Updates page title, meta tags, and canonical URL

## Troubleshooting

**Page shows "Loading..." forever:**
- Check browser console for errors
- Verify data file path is correct
- Ensure JSON file is valid (use JSONLint.com)

**Styling looks wrong:**
- For custom tables, ensure CSS classes are defined
- Check `tableClass` and `columnClasses` in JSON file

**Data not updating:**
- Clear browser cache
- Check for JSON syntax errors
- Verify file paths are absolute (start with `/`)
