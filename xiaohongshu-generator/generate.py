#!/usr/bin/env python3
"""
小红书图文生成器 - Xiaohongshu Card Generator
专业简洁风格 - Professional & Clean Style
"""

import sys
import os
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup
import urllib.request
import hashlib

# Configuration
CARD_SIZE = 1080
PADDING = 70
TITLE_FONT_SIZE = 52
BODY_FONT_SIZE = 26
LABEL_FONT_SIZE = 22
LINE_SPACING = 1.7
WATERMARK_TEXT = "pengandy.com"

# Professional color schemes - 专业简洁配色
COLOR_SCHEMES = [
    {
        'name': 'minimal_white',
        'bg': (255, 255, 255),           # 纯白
        'title': (26, 26, 26),           # 深黑
        'body': (80, 80, 80),            # 中灰
        'accent': (255, 107, 107),       # 活力红
        'tag_bg': (255, 245, 245),       # 浅红背景
    },
    {
        'name': 'soft_blue',
        'bg': (250, 252, 255),           # 浅蓝白
        'title': (30, 58, 138),          # 深蓝
        'body': (71, 85, 105),           # 蓝灰
        'accent': (59, 130, 246),        # 亮蓝
        'tag_bg': (239, 246, 255),       # 浅蓝背景
    },
    {
        'name': 'warm_cream',
        'bg': (255, 251, 245),           # 米白
        'title': (120, 53, 15),          # 棕色
        'body': (87, 83, 78),            # 暖灰
        'accent': (234, 88, 12),         # 橙色
        'tag_bg': (255, 247, 237),       # 浅橙背景
    },
    {
        'name': 'fresh_mint',
        'bg': (247, 254, 250),           # 薄荷白
        'title': (6, 78, 59),            # 深绿
        'body': (75, 85, 99),            # 冷灰
        'accent': (16, 185, 129),        # 翠绿
        'tag_bg': (236, 253, 245),       # 浅绿背景
    },
]

def download_image(url, output_dir):
    """Download image from URL and save to temp folder"""
    try:
        # Create temp folder for downloaded images
        temp_dir = os.path.join(output_dir, '.temp_images')
        Path(temp_dir).mkdir(parents=True, exist_ok=True)

        # Generate filename from URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = url.split('.')[-1].split('?')[0]  # Get extension, remove query params
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            ext = 'jpg'
        filename = f"{url_hash}.{ext}"
        filepath = os.path.join(temp_dir, filename)

        # Download if not already cached
        if not os.path.exists(filepath):
            urllib.request.urlretrieve(url, filepath)

        return filepath
    except Exception as e:
        print(f"⚠️  Could not download image from {url}: {e}")
        return None

def parse_html(html_file, output_dir='output'):
    """Extract H2/H3 headings and their content"""
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    cards = []
    html_dir = os.path.dirname(os.path.abspath(html_file))

    # Find the project root (where assets folder would be)
    # Assume blog posts are in blog/YEAR/POST/ structure
    base_path = html_dir
    while base_path and not os.path.exists(os.path.join(base_path, 'assets')):
        parent = os.path.dirname(base_path)
        if parent == base_path:  # Reached filesystem root
            break
        base_path = parent

    headings = soup.find_all(['h2', 'h3'])
    processed_elements = set()  # Track which elements we've already processed

    # Extract intro/preface content before first heading (前言)
    intro_content = []
    if headings:
        first_heading = headings[0]

        # Method 1: Check markdown-content div for quotes/intro (like bdrk1yo)
        markdown_div = soup.find('div', id='markdown-content')
        if markdown_div:
            for p in markdown_div.find_all('p', recursive=False):
                text = p.get_text().strip()
                if text and len(text) > 50:
                    intro_content.append(('text', text))
                    processed_elements.add(id(p))

        # Method 2: Find content between <hr> and first H2 (like serverless10yo)
        for elem in first_heading.find_previous_siblings():
            if elem.name == 'p':
                text = elem.get_text().strip()
                # Skip empty, very short, or metadata-like content
                # Check it doesn't look like navigation/tags (has '·' or lots of links)
                link_ratio = len(elem.find_all('a')) / max(1, len(text.split()))
                if text and len(text) > 80 and '·' not in text and link_ratio < 0.3:
                    intro_content.insert(0, ('text', text))
                    processed_elements.add(id(elem))
            elif elem.name == 'hr':
                # Stop at horizontal rule (usually marks end of header)
                break

    # Create introduction card if there's substantial intro content
    if intro_content:
        # Get blog title from h1.post-title
        blog_title_elem = soup.find('h1', class_='post-title')
        blog_title = blog_title_elem.get_text().strip() if blog_title_elem else "Introduction"

        cards.append({
            'title': blog_title,
            'content_items': intro_content[:3]  # Limit to first 3 intro paragraphs
        })

    for idx, heading in enumerate(headings):
        title = heading.get_text().strip()
        content_items = []  # Store items in order with type info

        # First, check for content BEFORE the heading (previous siblings)
        # Skip this for the first heading to avoid including general blog intro
        prev_siblings = []
        if idx > 0:  # Only process previous siblings for non-first headings
            for sibling in heading.find_previous_siblings():
                if sibling.name in ['h2', 'h3']:
                    break
                prev_siblings.insert(0, sibling)  # Insert at start to maintain order

        # Process previous siblings (content before heading)
        for sibling in prev_siblings:
            if id(sibling) in processed_elements:
                continue
            processed_elements.add(id(sibling))

            if sibling.name == 'p':
                text = sibling.get_text().strip()
                if text:
                    content_items.append(('text', text))
            elif sibling.name == 'li':
                text = sibling.get_text().strip()
                if text:
                    content_items.append(('text', '• ' + text))
            elif sibling.name == 'img':
                img_src = sibling.get('src')
                if img_src:
                    img_path = None
                    if img_src.startswith('http'):
                        img_path = download_image(img_src, output_dir)
                    else:
                        img_path = os.path.join(base_path, img_src.lstrip('/'))
                        if not os.path.exists(img_path):
                            img_path = None
                    if img_path:
                        content_items.append(('image', img_path))

            # Check for images inside elements
            img_tags = sibling.find_all('img') if hasattr(sibling, 'find_all') else []
            for img_tag in img_tags:
                img_src = img_tag.get('src')
                if img_src:
                    img_path = None
                    if img_src.startswith('http'):
                        img_path = download_image(img_src, output_dir)
                    else:
                        img_path = os.path.join(base_path, img_src.lstrip('/'))
                        if not os.path.exists(img_path):
                            img_path = None
                    if img_path:
                        content_items.append(('image', img_path))

        # Then process content AFTER the heading (next siblings)
        for sibling in heading.find_next_siblings():
            if sibling.name in ['h2', 'h3']:
                break
            if id(sibling) in processed_elements:
                continue
            processed_elements.add(id(sibling))

            if sibling.name == 'p':
                text = sibling.get_text().strip()
                if text:
                    content_items.append(('text', text))
            elif sibling.name == 'li':
                text = sibling.get_text().strip()
                if text:
                    content_items.append(('text', '• ' + text))
            elif sibling.name in ['ul', 'ol']:
                for li in sibling.find_all('li'):
                    text = li.get_text().strip()
                    if text:
                        content_items.append(('text', '• ' + text))
            elif sibling.name == 'table':
                # Extract content from tables (including lists in table cells)
                for cell in sibling.find_all(['td', 'th']):
                    # Get paragraphs in cells
                    for p in cell.find_all('p'):
                        text = p.get_text().strip()
                        if text:
                            content_items.append(('text', text))
                    # Get list items in cells
                    for li in cell.find_all('li'):
                        text = li.get_text().strip()
                        if text:
                            content_items.append(('text', '• ' + text))
            elif sibling.name == 'img':
                img_src = sibling.get('src')
                if img_src:
                    img_path = None
                    if img_src.startswith('http'):
                        img_path = download_image(img_src, output_dir)
                    else:
                        img_path = os.path.join(base_path, img_src.lstrip('/'))
                        if not os.path.exists(img_path):
                            img_path = None
                    if img_path:
                        content_items.append(('image', img_path))

            # Check for images inside elements
            img_tags = sibling.find_all('img') if hasattr(sibling, 'find_all') else []
            for img_tag in img_tags:
                img_src = img_tag.get('src')
                if img_src:
                    img_path = None
                    if img_src.startswith('http'):
                        img_path = download_image(img_src, output_dir)
                    else:
                        img_path = os.path.join(base_path, img_src.lstrip('/'))
                        if not os.path.exists(img_path):
                            img_path = None
                    if img_path:
                        content_items.append(('image', img_path))

        if content_items:
            # Smart limiting: if there are images, check if they'll overflow
            has_images = any(item_type == 'image' for item_type, _ in content_items)
            if has_images:
                # Find first image position
                first_img_pos = next(i for i, (t, _) in enumerate(content_items) if t == 'image')

                # Estimate if image will fit on same card with text
                # More realistic estimate: each text item averages 200px with spacing, image = 380px (with spacing)
                text_before_img = content_items[:first_img_pos]
                num_text_items = sum(1 for t, _ in text_before_img if t == 'text')

                # Calculate more accurate text height based on actual char counts
                total_text_chars = sum(len(c) for t, c in text_before_img if t == 'text')
                estimated_text_height = (total_text_chars // 50) * 45 + num_text_items * 20  # 45px per line + 20px spacing
                estimated_img_height = 380  # Image + spacing
                title_and_padding = 250  # Title, decorative line, spacing
                total_estimated_height = title_and_padding + estimated_text_height + estimated_img_height

                # Available space before watermark: CARD_SIZE(1080) - PADDING(70) - bottom_margin(105) = 905
                max_card_height = 880  # Be more conservative

                # If content would overflow, split into separate cards
                if total_estimated_height > max_card_height and num_text_items >= 2:
                    # Card 1: Text only (keep first 2-3 text items)
                    text_items = [item for item in content_items[:first_img_pos] if item[0] == 'text'][:3]
                    cards.append({
                        'title': title,
                        'content_items': text_items
                    })

                    # Card 2: Image + remaining content
                    image_and_after = [content_items[first_img_pos]] + content_items[first_img_pos+1:first_img_pos+3]
                    cards.append({
                        'title': f"{title} (cont.)",
                        'content_items': image_and_after
                    })
                else:
                    # Fits on one card - limit text before image
                    if first_img_pos > 2:
                        final_items = content_items[:2] + [content_items[first_img_pos]]
                    else:
                        final_items = content_items[:min(first_img_pos + 2, 6)]

                    # Truncate very long text items
                    truncated_items = []
                    for item_type, content in final_items:
                        if item_type == 'text' and len(content) > 180:
                            truncated_items.append((item_type, content[:180] + '...'))
                        else:
                            truncated_items.append((item_type, content))

                    cards.append({
                        'title': title,
                        'content_items': truncated_items
                    })
            else:
                # No images: can fit more text
                final_items = content_items[:12]
                cards.append({
                    'title': title,
                    'content_items': final_items
                })

    return cards

def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within max_width"""
    lines = []
    paragraphs = text.split('\n')

    for paragraph in paragraphs:
        if not paragraph.strip():
            continue

        words = paragraph.split()
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
            except:
                line_width = len(test_line) * 15

            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)

        if current_line:
            lines.append(' '.join(current_line))

    return lines

def generate_card_image(card, output_path, card_index, total_cards):
    """Generate professional Xiaohongshu-style card"""

    # Choose color scheme
    scheme = COLOR_SCHEMES[card_index % len(COLOR_SCHEMES)]

    # Create base image
    img = Image.new('RGB', (CARD_SIZE, CARD_SIZE), scheme['bg'])
    draw = ImageDraw.Draw(img)

    # Load fonts
    title_font = None
    body_font = None

    font_paths = [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Medium.ttc',
        '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                title_font = ImageFont.truetype(font_path, TITLE_FONT_SIZE)
                body_font = ImageFont.truetype(font_path, BODY_FONT_SIZE)
                label_font = ImageFont.truetype(font_path, LABEL_FONT_SIZE)
                break
            except:
                continue

    if not title_font:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        label_font = ImageFont.load_default()

    # Add card number badge (top right)
    badge_text = f"{card_index + 1}/{total_cards}"
    try:
        bbox = draw.textbbox((0, 0), badge_text, font=label_font)
        badge_width = bbox[2] - bbox[0] + 30
        badge_height = bbox[3] - bbox[1] + 20
    except:
        badge_width = len(badge_text) * 15 + 30
        badge_height = 40

    badge_x = CARD_SIZE - PADDING - badge_width
    badge_y = PADDING - 10

    # Badge background
    draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
        radius=20,
        fill=scheme['accent']
    )

    # Badge text
    text_x = badge_x + 15
    text_y = badge_y + 10
    draw.text((text_x, text_y), badge_text, fill=(255, 255, 255), font=label_font)

    # Start content
    y_position = PADDING + 80

    # Draw title with proper line wrapping
    content_width = CARD_SIZE - (2 * PADDING)
    title_lines = wrap_text(card['title'], title_font, content_width, draw)

    for line in title_lines[:2]:  # Max 2 lines for title
        draw.text(
            (PADDING, y_position),
            line,
            fill=scheme['title'],
            font=title_font
        )
        y_position += int(TITLE_FONT_SIZE * 1.2)

    # Decorative underline
    y_position += 20
    draw.rectangle(
        [(PADDING, y_position), (PADDING + 80, y_position + 5)],
        fill=scheme['accent']
    )

    y_position += 45

    # Draw content items in their original order
    content_items = card.get('content_items', [])
    img_max_width = CARD_SIZE - (2 * PADDING)

    # Calculate watermark line position
    watermark_line_y = CARD_SIZE - PADDING - 45

    # Detect if this is an image-focused card (single image or minimal text)
    num_images = sum(1 for t, _ in content_items if t == 'image')
    num_text = sum(1 for t, _ in content_items if t == 'text')
    total_text_chars = sum(len(c) for t, c in content_items if t == 'text')

    # Calculate available space for image dynamically
    if num_images >= 1 and (num_text == 0 or total_text_chars < 100):
        # Image-focused card: calculate max height based on available space
        # Leave margin for spacing above watermark line
        available_height = watermark_line_y - y_position - 40  # 40px margin before watermark
        img_max_height = min(680, available_height)  # Cap at 680px but don't overflow
    else:
        # Mixed content card: use smaller size to leave room for text
        img_max_height = 350

    max_y = watermark_line_y - 30  # Stop content 30px before watermark line

    for item_type, item_content in content_items:
        if y_position >= max_y:
            break

        if item_type == 'image':
            # Render image
            try:
                content_img = Image.open(item_content)

                # Resize while maintaining aspect ratio
                img_ratio = content_img.width / content_img.height
                if img_ratio > 1:  # Landscape
                    new_width = min(img_max_width, content_img.width)
                    new_height = int(new_width / img_ratio)
                else:  # Portrait or square
                    new_height = min(img_max_height, content_img.height)
                    new_width = int(new_height * img_ratio)

                # Ensure it fits
                if new_height > img_max_height:
                    new_height = img_max_height
                    new_width = int(new_height * img_ratio)
                if new_width > img_max_width:
                    new_width = img_max_width
                    new_height = int(new_width / img_ratio)

                content_img = content_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Center horizontally
                img_x = (CARD_SIZE - new_width) // 2
                img.paste(content_img, (img_x, y_position))

                y_position += new_height + 30
            except Exception as e:
                print(f"⚠️  Could not load image: {e}")

        elif item_type == 'text':
            # Render text
            if y_position >= max_y:
                break

            # Handle bullet points
            if item_content.strip().startswith('•'):
                bullet_size = 8
                bullet_x = PADDING + 5
                bullet_y = y_position + 12
                draw.ellipse(
                    [(bullet_x, bullet_y), (bullet_x + bullet_size, bullet_y + bullet_size)],
                    fill=scheme['accent']
                )
                content_x = PADDING + 28
                text_content = item_content.strip()[1:].strip()
            else:
                content_x = PADDING
                text_content = item_content

            # Wrap and draw text
            body_lines = wrap_text(text_content, body_font, content_width - 28, draw)

            for line in body_lines:
                if y_position >= max_y:
                    break

                draw.text(
                    (content_x, y_position),
                    line,
                    fill=scheme['body'],
                    font=body_font
                )
                y_position += int(BODY_FONT_SIZE * LINE_SPACING)

            y_position += 20  # Space between items

    # Bottom section
    bottom_y = CARD_SIZE - PADDING - 35

    # Subtle divider line
    draw.line(
        [(PADDING, bottom_y - 10), (CARD_SIZE - PADDING, bottom_y - 10)],
        fill=scheme['accent'],
        width=2
    )

    # Watermark
    draw.text(
        (PADDING, bottom_y + 5),
        WATERMARK_TEXT,
        fill=(150, 150, 150),
        font=label_font
    )

    # Small decorative accent (bottom right)
    accent_x = CARD_SIZE - PADDING - 15
    accent_y = bottom_y
    draw.rectangle(
        [(accent_x, accent_y), (accent_x + 15, accent_y + 30)],
        fill=scheme['accent']
    )

    # Save
    img.save(output_path, 'JPEG', quality=95)
    print(f"✅ {card_index + 1}/{total_cards} - {scheme['name']}")

def sanitize_filename(text):
    """Clean filename"""
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text[:50]

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate.py <html_file_path> [output_dir]")
        print("\nExample:")
        print("  python generate.py ../blog/2025/llm/index.html")
        sys.exit(1)

    html_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output'

    if not os.path.exists(html_file):
        print(f"❌ File not found: {html_file}")
        sys.exit(1)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"📖 Parsing: {html_file}")
    cards = parse_html(html_file, output_dir)
    print(f"📊 Found {len(cards)} cards\n")

    if not cards:
        print("❌ No H2/H3 headings found")
        sys.exit(1)

    print(f"🎨 Generating professional cards...")
    print(f"{'─' * 40}")

    for i, card in enumerate(cards):
        filename = f"{i+1}_{sanitize_filename(card['title'])}.jpg"
        output_path = os.path.join(output_dir, filename)
        generate_card_image(card, output_path, i, len(cards))

    print(f"{'─' * 40}")
    print(f"\n✨ Done! {len(cards)} cards → {output_dir}/")
    print(f"📂 open {output_dir}")

if __name__ == '__main__':
    main()
