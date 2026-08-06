import os

def create_initial_snake_svg(output_path):
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 160" width="100%" height="160">
  <rect width="850" height="160" fill="#0D1117" rx="8" />
  <style>
    .dot { rx: 2px; ry: 2px; }
    @keyframes snakeMove {
      0% { transform: translateX(0px); }
      50% { transform: translateX(350px); }
      100% { transform: translateX(0px); }
    }
    .snake-body { animation: snakeMove 8s ease-in-out infinite; }
  </style>

  <g transform="translate(20, 20)">
    <!-- Grid of contribution dots -->
'''
    
    # 52 weeks x 7 days grid
    for week in range(52):
        x = week * 15.5
        for day in range(7):
            y = day * 15.5
            # Color levels
            if (week + day) % 7 == 0:
                fill = "#A855F7" # Bright Purple
            elif (week * day) % 5 == 0:
                fill = "#06B6D4" # Cyan accent
            elif (week + day) % 3 == 0:
                fill = "#26A641" # Green
            elif (week + day) % 2 == 0:
                fill = "#161B22" # Low activity
            else:
                fill = "#21262D" # Empty
                
            svg_content += f'    <rect x="{x:.1f}" y="{y:.1f}" width="12" height="12" class="dot" fill="{fill}" opacity="0.85" />\n'

    # Animated Snake Body overlaying grid
    svg_content += '''
    <!-- Contribution Snake -->
    <g class="snake-body">
      <rect x="180" y="31" width="12" height="12" rx="3" fill="#06B6D4" filter="drop-shadow(0 0 4px #06B6D4)" />
      <rect x="164.5" y="31" width="12" height="12" rx="3" fill="#A855F7" />
      <rect x="149" y="31" width="12" height="12" rx="3" fill="#A855F7" />
      <rect x="133.5" y="31" width="12" height="12" rx="3" fill="#3B82F6" opacity="0.8" />
      <rect x="118" y="31" width="12" height="12" rx="3" fill="#3B82F6" opacity="0.5" />
    </g>
  </g>
</svg>'''
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(svg_content)
    print(f"Created snake SVG at: {output_path}")

if __name__ == "__main__":
    create_initial_snake_svg("/Users/studentuse33gmail.com/Desktop/economic-times-hackathon/assets/github-contribution-grid-snake-dark.svg")
    create_initial_snake_svg("/Users/studentuse33gmail.com/Desktop/economic-times-hackathon/assets/github-contribution-grid-snake.svg")
