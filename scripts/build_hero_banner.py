import os
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

def floyd_steinberg_dither(image_np):
    h, w = image_np.shape
    img = image_np.copy()
    for y in range(h):
        for x in range(w):
            old_val = img[y, x]
            new_val = 255.0 if old_val > 125.0 else 0.0
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

def get_pixel_rects(input_photo_path, grid_size=84, box_x=42, box_y=85, pixel_scale=1.75):
    img = Image.open(input_photo_path).convert("RGBA")
    np_img = np.array(img)
    r, g, b, a = np_img[:,:,0], np_img[:,:,1], np_img[:,:,2], np_img[:,:,3]
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    
    diff_rg = np.abs(r.astype(int) - g.astype(int))
    diff_gb = np.abs(g.astype(int) - b.astype(int))
    is_neutral_gray = (diff_rg < 35) & (diff_gb < 35)
    is_light_bg = (luminance > 165) & is_neutral_gray
    mask = np.where(is_light_bg, 0, 255).astype(np.uint8)
    
    width, height = img.size
    crop_size = int(min(width, height) * 0.86)
    left = (width - crop_size) // 2
    top = int(height * 0.08)
    right = left + crop_size
    bottom = top + crop_size
    
    img_cropped = img.crop((left, top, right, bottom))
    mask_cropped = Image.fromarray(mask).crop((left, top, right, bottom))
    
    gray_cropped = img_cropped.convert("L")
    gray_enhanced = ImageEnhance.Contrast(gray_cropped).enhance(1.5)
    gray_sharp = ImageEnhance.Sharpness(gray_enhanced).enhance(1.8)
    
    grid_img = gray_sharp.resize((grid_size, grid_size), resample=Image.Resampling.BILINEAR)
    grid_mask = mask_cropped.resize((grid_size, grid_size), resample=Image.Resampling.BILINEAR)
    
    grid_np = np.array(grid_img, dtype=np.float32)
    mask_np = np.array(grid_mask)
    
    dithered_np = floyd_steinberg_dither(grid_np)
    final_pixels = np.where(mask_np > 100, dithered_np, 0)
    
    rect_lines = []
    for y in range(grid_size):
        for x in range(grid_size):
            if mask_np[y, x] > 100 and final_pixels[y, x] > 128:
                px = box_x + (x * pixel_scale)
                py = box_y + (y * pixel_scale)
                
                # Dynamic accent coloring
                if y < grid_size * 0.22 and (x + y) % 8 == 0:
                    cls = 'fill="#A855F7" opacity="0.95"'
                elif y > grid_size * 0.78 and (x + y) % 6 == 0:
                    cls = 'fill="#06B6D4" opacity="0.95"'
                elif (x * y + y) % 17 == 0:
                    cls = 'fill="#3B82F6" opacity="0.9"'
                else:
                    cls = 'fill="#E6EDF3" opacity="0.88"'
                rect_lines.append(f'<rect x="{px:.2f}" y="{py:.2f}" width="{pixel_scale:.2f}" height="{pixel_scale:.2f}" {cls} rx="0.3" />')
                
    return "\n".join(rect_lines)

def build_hero_banner():
    photo_path = "/Users/studentuse33gmail.com/.gemini/antigravity-ide/brain/17863d77-569e-42f0-8e94-7c36a8b83618/media__1786012578703.jpg"
    out_banner_path = "/Users/studentuse33gmail.com/Desktop/economic-times-hackathon/assets/banner.svg"
    
    pixel_rects_svg = get_pixel_rects(photo_path)
    
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 440" width="100%" height="100%">
  <defs>
    <!-- Dark background gradient -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0D1117" />
      <stop offset="50%" stop-color="#161B22" />
      <stop offset="100%" stop-color="#0D1117" />
    </linearGradient>

    <!-- Glassmorphism stroke gradient -->
    <linearGradient id="borderGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#A855F7" stop-opacity="0.8" />
      <stop offset="50%" stop-color="#3B82F6" stop-opacity="0.4" />
      <stop offset="100%" stop-color="#06B6D4" stop-opacity="0.8" />
    </linearGradient>

    <!-- Accent text gradient -->
    <linearGradient id="textGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#A855F7" />
      <stop offset="50%" stop-color="#3B82F6" />
      <stop offset="100%" stop-color="#06B6D4" />
    </linearGradient>
    
    <!-- Neon glow filter -->
    <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
    
    <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&amp;family=Inter:wght@400;500;600;700&amp;display=swap');

    .term-text {{ font-family: 'JetBrains Mono', monospace; }}
    .ui-text {{ font-family: 'Inter', sans-serif; }}

    /* Pulsing Cursor */
    @keyframes cursorPulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0; }}
    }}
    .cursor {{
      animation: cursorPulse 1s infinite;
      fill: #06B6D4;
    }}

    /* Glow breathe animation */
    @keyframes glowBreathe {{
      0%, 100% {{ stroke-opacity: 0.6; filter: drop-shadow(0 0 4px rgba(168, 85, 247, 0.3)); }}
      50% {{ stroke-opacity: 0.95; filter: drop-shadow(0 0 10px rgba(6, 182, 212, 0.6)); }}
    }}
    .glowing-frame {{
      animation: glowBreathe 4s ease-in-out infinite;
    }}

    /* Status dot pulse */
    @keyframes statusPulse {{
      0%, 100% {{ r: 4.5px; opacity: 1; }}
      50% {{ r: 6.5px; opacity: 0.6; }}
    }}
    .status-dot {{
      animation: statusPulse 2s ease-in-out infinite;
      fill: #22C55E;
    }}

    /* Fade in animation */
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .animate-fade {{ animation: fadeIn 0.8s ease-out forwards; }}
  </style>

  <!-- Main Background Container -->
  <rect width="880" height="440" rx="14" fill="url(#bgGrad)" stroke="url(#borderGrad)" stroke-width="1.5" />

  <!-- Window Header Bar -->
  <rect width="880" height="38" rx="14" fill="#161B22" />
  <rect y="24" width="880" height="14" fill="#161B22" />
  <line x1="0" y1="38" x2="880" y2="38" stroke="#30363D" stroke-width="1" />

  <!-- Mac Window Controls -->
  <circle cx="24" cy="19" r="6" fill="#FF5F56" />
  <circle cx="44" cy="19" r="6" fill="#FFBD2E" />
  <circle cx="64" cy="19" r="6" fill="#27C93F" />

  <!-- Window Title -->
  <text x="440" y="24" text-anchor="middle" fill="#8B949E" font-size="12.5" class="term-text" font-weight="500">profile.sh — live</text>

  <!-- Content Container Grid -->
  <!-- LEFT: Pixel Portrait Frame (Glassmorphic Container) -->
  <g class="animate-fade">
    <!-- Frame Outer Accent Glow -->
    <rect x="32" y="60" width="168" height="212" rx="10" fill="#161B22" fill-opacity="0.75" stroke="url(#borderGrad)" stroke-width="1.5" class="glowing-frame" />
    
    <!-- Portrait Background Accent Grid -->
    <rect x="40" y="68" width="152" height="196" rx="6" fill="#0D1117" stroke="#30363D" stroke-width="1" />
    
    <!-- Dithered Floyd-Steinberg Pixel Portrait Rects -->
    <g class="portrait-grid">
{pixel_rects_svg}
    </g>

    <!-- Portrait Footer Label -->
    <rect x="48" y="234" width="136" height="22" rx="4" fill="#161B22" fill-opacity="0.9" stroke="#30363D" stroke-width="0.8" />
    <text x="116" y="249" text-anchor="middle" fill="#A855F7" font-size="10.5" class="term-text" font-weight="700">AYUSH.RAW</text>
  </g>

  <!-- RIGHT: Terminal Content Header & System Info Panel -->
  <g transform="translate(222, 58)">
    
    <!-- Main Heading -->
    <text x="0" y="32" fill="url(#textGrad)" font-size="28" font-weight="700" class="term-text" letter-spacing="1">AYUSH SINGH<tspan class="cursor">_</tspan></text>
    
    <!-- Subtitle -->
    <text x="0" y="54" fill="#06B6D4" font-size="13" font-weight="600" class="term-text">AI Engineer <tspan fill="#6E7681">•</tspan> Full Stack Developer <tspan fill="#6E7681">•</tspan> DSA Enthusiast</text>
    
    <!-- Tagline -->
    <text x="0" y="74" fill="#8B949E" font-size="12" font-style="italic" class="ui-text">"Building intelligent software one commit at a time."</text>

    <!-- SYSTEM.INFO HUD Panel -->
    <rect x="0" y="92" width="624" height="268" rx="10" fill="#161B22" fill-opacity="0.6" stroke="#30363D" stroke-width="1" />

    <!-- HUD Panel Header Bar -->
    <path d="M 0 102 A 10 10 0 0 1 10 92 L 614 92 A 10 10 0 0 1 624 102 L 624 120 L 0 120 Z" fill="#21262D" />
    <line x1="0" y1="120" x2="624" y2="120" stroke="#30363D" stroke-width="1" />
    
    <text x="14" y="112" fill="#A855F7" font-size="11" font-weight="700" class="term-text">SYSTEM.INFO</text>
    <text x="520" y="112" fill="#8B949E" font-size="10" class="term-text">SYS_ID: 840-AI</text>

    <!-- HUD Grid Info Rows -->
    <g transform="translate(16, 138)" class="ui-text">
      
      <!-- Status Row -->
      <g transform="translate(0, 0)">
        <text x="0" y="12" fill="#8B949E" font-size="11.5" font-weight="600" class="term-text">STATUS</text>
        <text x="90" y="12" fill="#8B949E" font-size="11.5">:</text>
        <circle cx="106" cy="8" r="4.5" class="status-dot" />
        <text x="118" y="12" fill="#3FB950" font-size="12" font-weight="600" class="term-text">Building. Learning. Shipping.</text>
      </g>

      <!-- Education Row -->
      <g transform="translate(0, 26)">
        <text x="0" y="12" fill="#8B949E" font-size="11.5" font-weight="600" class="term-text">EDUCATION</text>
        <text x="90" y="12" fill="#8B949E" font-size="11.5">:</text>
        <text x="104" y="12" fill="#E6EDF3" font-size="12">B.Tech Computer Science (AI &amp; ML)</text>
        <text x="345" y="12" fill="#8B949E" font-size="11">@ Newton School of Tech</text>
      </g>

      <!-- Location Row -->
      <g transform="translate(0, 52)">
        <text x="0" y="12" fill="#8B949E" font-size="11.5" font-weight="600" class="term-text">LOCATION</text>
        <text x="90" y="12" fill="#8B949E" font-size="11.5">:</text>
        <text x="104" y="12" fill="#E6EDF3" font-size="12">Patna, Bihar, India 🇮🇳</text>
      </g>

      <!-- Core Stack Badges Grid -->
      <g transform="translate(0, 78)">
        <text x="0" y="12" fill="#8B949E" font-size="11.5" font-weight="600" class="term-text">STACK</text>
        <text x="90" y="12" fill="#8B949E" font-size="11.5">:</text>

        <!-- Stack Pills -->
        <!-- Python -->
        <rect x="104" y="-1" width="58" height="18" rx="4" fill="#1F2937" stroke="#3B82F6" stroke-width="0.8" />
        <text x="133" y="12" text-anchor="middle" fill="#60A5FA" font-size="10.5" class="term-text" font-weight="600">Python</text>

        <!-- C++ -->
        <rect x="168" y="-1" width="42" height="18" rx="4" fill="#1F2937" stroke="#06B6D4" stroke-width="0.8" />
        <text x="189" y="12" text-anchor="middle" fill="#22D3EE" font-size="10.5" class="term-text" font-weight="600">C++</text>

        <!-- JS / React -->
        <rect x="216" y="-1" width="52" height="18" rx="4" fill="#1F2937" stroke="#A855F7" stroke-width="0.8" />
        <text x="242" y="12" text-anchor="middle" fill="#C084FC" font-size="10.5" class="term-text" font-weight="600">React</text>

        <!-- Node.js -->
        <rect x="274" y="-1" width="54" height="18" rx="4" fill="#1F2937" stroke="#22C55E" stroke-width="0.8" />
        <text x="301" y="12" text-anchor="middle" fill="#4ADE80" font-size="10.5" class="term-text" font-weight="600">Node.js</text>

        <!-- Docker -->
        <rect x="334" y="-1" width="56" height="18" rx="4" fill="#1F2937" stroke="#3B82F6" stroke-width="0.8" />
        <text x="362" y="12" text-anchor="middle" fill="#93C5FD" font-size="10.5" class="term-text" font-weight="600">Docker</text>

        <!-- RAG / AI -->
        <rect x="396" y="-1" width="56" height="18" rx="4" fill="#1F2937" stroke="#A855F7" stroke-width="0.8" />
        <text x="424" y="12" text-anchor="middle" fill="#E879F9" font-size="10.5" class="term-text" font-weight="600">RAG/AI</text>
      </g>

      <!-- Bottom Quick Contact Grid -->
      <g transform="translate(0, 114)">
        <line x1="0" y1="0" x2="592" y2="0" stroke="#30363D" stroke-width="0.8" stroke-dasharray="4 4" />
        
        <text x="0" y="20" fill="#8B949E" font-size="11.5" font-weight="600" class="term-text">CONNECT</text>
        <text x="90" y="20" fill="#8B949E" font-size="11.5">:</text>

        <text x="104" y="20" fill="#58A6FF" font-size="11" class="term-text">GitHub: github.com/Ayush-840</text>
        <text x="345" y="20" fill="#06B6D4" font-size="11" class="term-text">Email: singhayushkumar5555@gmail.com</text>
      </g>
    </g>
  </g>
  
  <!-- Outer Corner Accents -->
  <path d="M 14 0 L 0 14" stroke="#A855F7" stroke-width="2" />
  <path d="M 866 440 L 880 426" stroke="#06B6D4" stroke-width="2" />
</svg>
'''
    os.makedirs(os.path.dirname(out_banner_path), exist_ok=True)
    with open(out_banner_path, "w") as f:
        f.write(svg_content)
    print(f"Hero banner SVG successfully written to: {out_banner_path}")

if __name__ == "__main__":
    build_hero_banner()
