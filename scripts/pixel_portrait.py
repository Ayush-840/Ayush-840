import os
import sys
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

def floyd_steinberg_dither(image_np):
    """
    Applies Floyd-Steinberg dithering on a 2D float numpy array (0.0 to 255.0).
    Returns a binary array (0 or 255).
    """
    h, w = image_np.shape
    img = image_np.copy()
    
    for y in range(h):
        for x in range(w):
            old_val = img[y, x]
            new_val = 255.0 if old_val > 128.0 else 0.0
            img[y, x] = new_val
            err = old_val - new_val
            
            if x + 1 < w:
                img[y, x + 1] += err * (7.0 / 16.0)
            if y + 1 < h:
                if x - 1 >= 0:
                    img[y + 1, x - 1] += err * (3.0 / 16.0)
                img[y + 1, x] += err * (5.0 / 16.0)
                if x + 1 < w:
                    img[y + 1, x + 1] += err * (1.0 / 16.0)
                    
    return np.clip(img, 0, 255).astype(np.uint8)

def process_portrait(input_path, output_png_path, output_svg_path, grid_size=120):
    print(f"Loading input photo from: {input_path}")
    img = Image.open(input_path).convert("RGBA")
    
    # 1. Background removal / segmentation
    np_img = np.array(img)
    r, g, b, a = np_img[:,:,0], np_img[:,:,1], np_img[:,:,2], np_img[:,:,3]
    
    # Calculate luminance
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    
    # Background is high luminance studio background (gray/white studio gradient)
    diff_rg = np.abs(r.astype(int) - g.astype(int))
    diff_gb = np.abs(g.astype(int) - b.astype(int))
    is_neutral_gray = (diff_rg < 35) & (diff_gb < 35)
    # The studio background has luminance > 165
    is_light_bg = (luminance > 165) & is_neutral_gray
    
    # Create mask: 255 for subject, 0 for background
    mask = np.where(is_light_bg, 0, 255).astype(np.uint8)
    
    # Square crop focused on face & upper body
    width, height = img.size
    crop_size = int(min(width, height) * 0.88)
    left = (width - crop_size) // 2
    top = int(height * 0.08)  # Position to frame head and shoulders perfectly
    right = left + crop_size
    bottom = top + crop_size
    
    img_cropped = img.crop((left, top, right, bottom))
    mask_cropped = Image.fromarray(mask).crop((left, top, right, bottom))

    
    # Convert cropped to grayscale
    gray_cropped = img_cropped.convert("L")
    
    # Contrast enhancement
    enhancer = ImageEnhance.Contrast(gray_cropped)
    gray_enhanced = enhancer.enhance(1.45)
    
    # Sharpen key facial features (eyes, hair, beard)
    sharpener = ImageEnhance.Sharpness(gray_enhanced)
    gray_sharp = sharpener.enhance(1.8)
    
    # Resize to pixel grid size
    grid_img = gray_sharp.resize((grid_size, grid_size), resample=Image.Resampling.BILINEAR)
    grid_mask = mask_cropped.resize((grid_size, grid_size), resample=Image.Resampling.BILINEAR)
    
    grid_np = np.array(grid_img, dtype=np.float32)
    mask_np = np.array(grid_mask)
    
    # Apply Floyd-Steinberg dithering to the subject area
    dithered_np = floyd_steinberg_dither(grid_np)
    
    # Set background area to 0
    final_pixels = np.where(mask_np > 100, dithered_np, 0)
    
    # 2. Output crisp PNG (scaled up 4x for preview)
    scale = 4
    out_img = Image.fromarray(final_pixels, mode="L").resize(
        (grid_size * scale, grid_size * scale), resample=Image.Resampling.NEAREST
    )
    
    # Create RGBA PNG with dark theme styling (#F0F6FC for highlights, transparent background)
    rgba_data = np.zeros((grid_size * scale, grid_size * scale, 4), dtype=np.uint8)
    fg_mask = np.array(out_img) > 128
    rgba_data[fg_mask] = [240, 246, 252, 255] # Clean dithered highlights
    
    final_png = Image.fromarray(rgba_data, "RGBA")
    os.makedirs(os.path.dirname(output_png_path), exist_ok=True)
    final_png.save(output_png_path)
    print(f"Saved dithered PNG to: {output_png_path}")
    
    # 3. Output SVG rect grid representation
    generate_svg_pixel_art(final_pixels, mask_np, output_svg_path, grid_size)

def generate_svg_pixel_art(pixel_data, mask_data, svg_path, grid_size):
    """
    Generates an optimized SVG pixel art representation.
    """
    pixel_size = 2.5
    svg_width = grid_size * pixel_size
    svg_height = grid_size * pixel_size
    
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}" height="{svg_height}">',
        '  <style>',
        '    .px-fg { fill: #E6EDF3; }',
        '    .px-accent { fill: #A855F7; }',
        '    .px-cyan { fill: #06B6D4; }',
        '  </style>',
        '  <g class="pixel-art-grid">'
    ]
    
    for y in range(grid_size):
        for x in range(grid_size):
            if mask_data[y, x] > 100:
                val = pixel_data[y, x]
                if val > 128:
                    px_x = x * pixel_size
                    px_y = y * pixel_size
                    # Add subtle color accents to top highlights
                    if y < grid_size * 0.2 and (x + y) % 9 == 0:
                        cls = "px-accent"
                    elif y > grid_size * 0.8 and (x + y) % 7 == 0:
                        cls = "px-cyan"
                    else:
                        cls = "px-fg"
                    svg_lines.append(f'    <rect x="{px_x}" y="{px_y}" width="{pixel_size}" height="{pixel_size}" class="{cls}" />')
                    
    svg_lines.append('  </g>')
    svg_lines.append('</svg>')
    
    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, "w") as f:
        f.write("\n".join(svg_lines))
    print(f"Saved dithered SVG grid to: {svg_path}")

if __name__ == "__main__":
    input_img = "/Users/studentuse33gmail.com/.gemini/antigravity-ide/brain/17863d77-569e-42f0-8e94-7c36a8b83618/media__1786012578703.jpg"
    out_png = "/Users/studentuse33gmail.com/Desktop/economic-times-hackathon/assets/portrait_pixel.png"
    out_svg = "/Users/studentuse33gmail.com/Desktop/economic-times-hackathon/assets/portrait_pixel.svg"
    process_portrait(input_img, out_png, out_svg)
