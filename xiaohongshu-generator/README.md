# 小红书图文生成器 (Xiaohongshu Card Generator)

A simple CLI tool to convert blog posts into 1:1 square knowledge cards (知识小卡片) for Xiaohongshu.

## Features

✨ **Simple Command Line** - One command to generate all cards
📖 **Auto Extract** - Extracts H2/H3 headings from HTML
🎨 **Clean Design** - Professional knowledge card style
📱 **Perfect Format** - 1080x1080 JPG images
🔖 **Watermark** - Customizable branding
🚀 **Local & Fast** - No internet required, runs locally

## Quick Start

### 1. Install Dependencies

```bash
pip3 install --user beautifulsoup4 Pillow
```

### 2. Generate Cards

```bash
python3 generate.py <html_file_path> [output_dir]
```

**Example:**
```bash
# Generate from blog post
python3 generate.py ../blog/2025/llm/index.html

# Custom output folder
python3 generate.py ../blog/2025/llm/index.html my-cards/

# Any HTML file
python3 generate.py /path/to/your/post.html output/
```

### 3. Get Your Images

Images are saved in the `output/` folder (or your custom folder):
```
output/
├── 1_Foundation_Model_Open_Source_vs_Closed_Source.jpg
├── 2_Academia_vs_Industry_Fusion.jpg
├── 3_LLM_Native_Open_Source_Ecosystem_in_Place.jpg
└── ...
```

## How It Works

1. **Parses HTML** - Finds all H2 and H3 headings
2. **Extracts Content** - Gets paragraphs and lists after each heading
3. **Creates Cards** - One card per heading with title + content
4. **Generates Images** - 1080x1080 JPG with clean layout
5. **Adds Watermark** - Your brand in bottom-right corner

## Customization

Edit `generate.py` to customize:

```python
# Image size (default: 1080x1080)
CARD_SIZE = 1080

# Padding around content
PADDING = 40

# Font sizes
TITLE_FONT_SIZE = 32
BODY_FONT_SIZE = 18

# Watermark text
WATERMARK_TEXT = "pengandy.com"

# Colors
BG_COLOR = (255, 255, 255)        # White background
TITLE_COLOR = (26, 26, 26)         # Dark title
BODY_COLOR = (68, 68, 68)          # Gray body text
WATERMARK_COLOR = (153, 153, 153)  # Light gray watermark
```

## Requirements

- Python 3.6+
- beautifulsoup4
- Pillow (PIL)

## Usage Examples

### Example 1: Basic Usage
```bash
python3 generate.py blog/2025/llm/index.html
```
Output: `output/1_Title.jpg`, `output/2_Title.jpg`, ...

### Example 2: Custom Output Folder
```bash
python3 generate.py blog/2025/llm/index.html xiaohongshu-cards/
```
Output: `xiaohongshu-cards/1_Title.jpg`, ...

### Example 3: Multiple Posts
```bash
# Generate cards for all blog posts
for post in blog/2025/*/index.html; do
    python3 generate.py "$post" "output/$(basename $(dirname $post))/"
done
```

## What Gets Extracted

The tool extracts content based on heading structure:

```html
<h2>This becomes the card title</h2>
<p>This paragraph goes in the card body</p>
<p>This one too</p>
<ul>
  <li>List items are also included</li>
</ul>

<h2>Next card title</h2>
<p>Content for the second card...</p>
```

**Result:** 2 cards
- Card 1: Title from first H2, content from following paragraphs/lists
- Card 2: Title from second H2, content from its paragraphs/lists

## Troubleshooting

### No cards generated
**Issue:** `No H2/H3 headings found in the HTML file`

**Solution:** Check if your HTML has `<h2>` or `<h3>` tags

### Unicode errors
**Issue:** Special characters not displaying correctly

**Solution:** The script automatically tries multiple fonts. If issues persist, edit the font list in `generate.py`:
```python
for font_path in [
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',  # Best for Unicode
    '/System/Library/Fonts/PingFang.ttc',                    # Chinese
    '/System/Library/Fonts/Helvetica.ttc',                   # Fallback
]:
```

### Permission denied
**Issue:** Can't install packages

**Solution:** Use `--user` flag:
```bash
pip3 install --user beautifulsoup4 Pillow
```

## Output Format

Each image is:
- **Size:** 1080x1080 pixels (1:1 square)
- **Format:** JPEG
- **Quality:** 92% (high quality, reasonable file size)
- **Layout:**
  - Top: Title (bold, 32px)
  - Middle: Content paragraphs (18px, max 5 paragraphs)
  - Bottom: Watermark (right-aligned, subtle)

## Tips

1. **File naming:** Cards are numbered and use sanitized heading text
2. **Content limit:** Max 5 paragraphs per card to avoid overflow
3. **Image size:** 1080x1080 is recommended for Xiaohongshu
4. **Batch processing:** Loop through multiple files for bulk generation

## License

MIT License - See LICENSE file

## Author

Created for easy Xiaohongshu content creation from blog posts.
