"""
Enhanced Telescope Eyepiece View with Constellation Mode
This module adds augmented reality constellation overlays to the telescope view
"""

import math
from PIL import Image, ImageDraw, ImageFont
from constellation_patterns import CONSTELLATION_LINES, CONSTELLATION_FIGURES

class EnhancedEyepieceView:
    """
    Simulates a telescope eyepiece with AR constellation overlays
    In real hardware, this would overlay on live camera feed
    """
    
    def __init__(self, width=1200, height=1200):
        self.width = width
        self.height = height
        self.constellation_mode = False
        self.show_labels = True
        self.show_constellation_art = False
        
    def calculate_star_position(self, star_ra, star_dec, center_ra, center_dec, fov):
        """
        Convert star RA/Dec to pixel coordinates on the display
        Uses gnomonic projection (tangent plane projection)
        """
        # Convert to radians
        star_ra_rad = math.radians(star_ra)
        star_dec_rad = math.radians(star_dec)
        center_ra_rad = math.radians(center_ra)
        center_dec_rad = math.radians(center_dec)
        
        # Calculate relative position using gnomonic projection
        cos_c = (math.sin(center_dec_rad) * math.sin(star_dec_rad) + 
                 math.cos(center_dec_rad) * math.cos(star_dec_rad) * 
                 math.cos(star_ra_rad - center_ra_rad))
        
        if cos_c <= 0:
            return None, None  # Star is behind the view plane
        
        x_proj = (math.cos(star_dec_rad) * math.sin(star_ra_rad - center_ra_rad)) / cos_c
        y_proj = (math.cos(center_dec_rad) * math.sin(star_dec_rad) - 
                  math.sin(center_dec_rad) * math.cos(star_dec_rad) * 
                  math.cos(star_ra_rad - center_ra_rad)) / cos_c
        
        # Convert to pixel coordinates
        # Scale based on field of view
        scale = (self.width / 2) / math.tan(math.radians(fov))
        
        pixel_x = self.width / 2 + x_proj * scale
        pixel_y = self.height / 2 - y_proj * scale  # Flip Y axis
        
        return pixel_x, pixel_y
    
    def draw_star(self, draw, x, y, magnitude, color='white'):
        """
        Draw a star with size based on magnitude
        Brighter stars (lower magnitude) are larger
        """
        # Convert magnitude to pixel size (inverted scale)
        size = max(2, int(15 - magnitude * 2))
        
        # Draw star with glow effect
        # Outer glow
        for i in range(3, 0, -1):
            alpha = int(255 / (i + 1))
            glow_color = self._blend_color(color, (0, 0, 0), 0.3 * i)
            draw.ellipse(
                [x - size - i, y - size - i, x + size + i, y + size + i],
                fill=glow_color,
                outline=None
            )
        
        # Core star
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=color,
            outline=color
        )
        
        # Add cross-hairs for bright stars
        if magnitude < 2.0:
            spike_len = size + 8
            draw.line([x - spike_len, y, x + spike_len, y], fill=color, width=1)
            draw.line([x, y - spike_len, x, y + spike_len], fill=color, width=1)
    
    def _blend_color(self, color, bg_color, alpha):
        """Blend color with background"""
        if isinstance(color, str):
            color = self._hex_to_rgb(color)
        if isinstance(bg_color, str):
            bg_color = self._hex_to_rgb(bg_color)
        
        r = int(color[0] * alpha + bg_color[0] * (1 - alpha))
        g = int(color[1] * alpha + bg_color[1] * (1 - alpha))
        b = int(color[2] * alpha + bg_color[2] * (1 - alpha))
        return (r, g, b)
    
    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def get_star_color(self, spectral_type):
        """Get color based on spectral type"""
        colors = {
            'O': '#4a9eff',  # Blue
            'B': '#6bb6ff',  # Blue-white
            'A': '#ffffff',  # White
            'F': '#fff9e6',  # Yellow-white
            'G': '#ffeb3b',  # Yellow (like our Sun)
            'K': '#ff9800',  # Orange
            'M': '#ff5722'   # Red
        }
        return colors.get(spectral_type.upper(), '#ffffff')
    
    def draw_constellation_lines(self, draw, stars_in_view, stars_db, constellation_name):
        """
        Draw lines connecting stars to form constellation patterns
        """
        if constellation_name not in CONSTELLATION_LINES:
            return
        
        # Create a lookup dict for quick star position finding
        star_positions = {}
        for star in stars_in_view:
            star_positions[star['name'].lower()] = (star['pixel_x'], star['pixel_y'])
        
        # Draw each line in the constellation
        lines_drawn = 0
        for star1_name, star2_name in CONSTELLATION_LINES[constellation_name]:
            star1_name = star1_name.lower()
            star2_name = star2_name.lower()
            
            if star1_name in star_positions and star2_name in star_positions:
                x1, y1 = star_positions[star1_name]
                x2, y2 = star_positions[star2_name]
                
                # Draw constellation line in cyan
                draw.line(
                    [x1, y1, x2, y2],
                    fill='#00ffff',
                    width=2
                )
                lines_drawn += 1
        
        return lines_drawn
    
    def render_eyepiece_view(self, stars, stars_db, center_ra, center_dec, fov, 
                            constellation_mode=None, filename='eyepiece_view.png'):
        """
        Main rendering function - creates the eyepiece view image
        
        Args:
            stars: List of star objects in field of view
            stars_db: Full star database for looking up info
            center_ra, center_dec: Telescope pointing coordinates
            fov: Field of view in degrees
            constellation_mode: Which constellation to highlight (or None)
        """
        # Create black space background
        img = Image.new('RGB', (self.width, self.height), color='#000000')
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        try:
            label_font = ImageFont.truetype("arial.ttf", 14)
            title_font = ImageFont.truetype("arial.ttf", 24)
            info_font = ImageFont.truetype("arial.ttf", 16)
        except:
            label_font = ImageFont.load_default()
            title_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
        
        # Calculate pixel positions for all stars
        stars_in_view = []
        for star in stars:
            star_data = stars_db.get(star['name'].lower(), {})
            
            try:
                star_ra = float(star_data.get('ra', 0))
                star_dec = float(star_data.get('dec', 0))
            except:
                continue
            
            pixel_x, pixel_y = self.calculate_star_position(
                star_ra, star_dec, center_ra, center_dec, fov
            )
            
            # Check if star is within image bounds
            if (pixel_x and pixel_y and 
                0 <= pixel_x < self.width and 
                0 <= pixel_y < self.height):
                
                stars_in_view.append({
                    'name': star['name'],
                    'pixel_x': pixel_x,
                    'pixel_y': pixel_y,
                    'magnitude': star.get('mag', 5.0),
                    'spectral_type': star_data.get('type', 'G'),
                    'constellation': star_data.get('constellation', 'Unknown')
                })
        
        # Draw constellation lines FIRST (so they appear behind stars)
        if constellation_mode and constellation_mode in CONSTELLATION_LINES:
            lines_drawn = self.draw_constellation_lines(
                draw, stars_in_view, stars_db, constellation_mode
            )
            
            # Draw constellation name at top
            const_text = f"🌌 {constellation_mode.upper()} 🌌"
            draw.text(
                (self.width // 2, 30),
                const_text,
                fill='#00ffff',
                font=title_font,
                anchor='mt'
            )
        
        # Draw all stars
        for star in stars_in_view:
            color = self.get_star_color(star['spectral_type'])
            self.draw_star(
                draw,
                star['pixel_x'],
                star['pixel_y'],
                star['magnitude'],
                color
            )
            
            # Draw star labels if enabled
            if self.show_labels and star['magnitude'] < 3.0:
                label_text = star['name'].title()
                draw.text(
                    (star['pixel_x'] + 15, star['pixel_y'] - 5),
                    label_text,
                    fill='#ffffff',
                    font=label_font
                )
        
        # Draw crosshair at center
        center_x, center_y = self.width // 2, self.height // 2
        crosshair_size = 30
        draw.line(
            [center_x - crosshair_size, center_y, center_x + crosshair_size, center_y],
            fill='#00ff00',
            width=2
        )
        draw.line(
            [center_x, center_y - crosshair_size, center_x, center_y + crosshair_size],
            fill='#00ff00',
            width=2
        )
        draw.ellipse(
            [center_x - 5, center_y - 5, center_x + 5, center_y + 5],
            outline='#00ff00',
            width=2
        )
        
        # Draw FOV circle
        fov_radius = (self.width / 2) * 0.9
        draw.ellipse(
            [center_x - fov_radius, center_y - fov_radius,
             center_x + fov_radius, center_y + fov_radius],
            outline='#333333',
            width=2
        )
        
        # Draw info panel at bottom
        info_text = f"RA: {center_ra:.2f}°  |  Dec: {center_dec:.2f}°  |  FOV: {fov*2:.1f}°  |  Stars: {len(stars_in_view)}"
        draw.text(
            (self.width // 2, self.height - 30),
            info_text,
            fill='#888888',
            font=info_font,
            anchor='mt'
        )
        
        # Add mode indicator
        if constellation_mode:
            mode_text = "CONSTELLATION MODE: ON"
            draw.rectangle(
                [10, 10, 280, 50],
                fill='#003333',
                outline='#00ffff',
                width=2
            )
            draw.text(
                (145, 30),
                mode_text,
                fill='#00ffff',
                font=info_font,
                anchor='mt'
            )
        
        # Save image
        img.save(filename)
        print(f"✅ Eyepiece view saved as: {filename}")
        return img


def enhanced_telescope_view(stars, stars_db, telescope_hw, planets=None, 
                            planet_positions=None, moon_position=None):
    """
    Enhanced telescope view with constellation overlay mode
    Replaces the original telescope_view function
    """
    print("\n" + "=" * 70)
    print("🔭 ENHANCED EYEPIECE VIEW 🔭")
    print("=" * 70)
    
    # Get current telescope position
    current_ra, current_dec = telescope_hw.get_position()
    print(f"Current Pointing: RA {current_ra:.2f}°, Dec {current_dec:.2f}°")
    
    # Field of view
    fov = 5.0  # Wider FOV for better constellation viewing
    
    print(f"Scanning field of view ({fov*2:.1f}° diameter)...")
    print("-" * 70)
    
    # Find all objects in view
    objects_in_view = []
    
    # Check Stars
    for name, data in stars_db.items():
        if data.get('ra') == "Unknown": 
            continue
        try:
            star_ra = float(data['ra'])
            star_dec = float(data['dec'])
            
            # Calculate angular distance from center
            distance = calculate_angular_distance(
                current_ra, current_dec, star_ra, star_dec
            )
            
            if distance <= fov:
                mag = float(data.get('magnitude', 6))
                if mag < 6.5:  # Only visible stars
                    objects_in_view.append({
                        'name': name,
                        'type': 'star',
                        'distance_deg': distance,
                        'mag': mag,
                        'ra': star_ra,
                        'dec': star_dec
                    })
        except:
            continue
    
    # Sort by brightness
    objects_in_view.sort(key=lambda x: x['mag'])
    
    print(f"✨ Found {len(objects_in_view)} stars in field of view")
    
    # Identify which constellation(s) are visible
    constellations_present = set()
    for obj in objects_in_view:
        if obj['type'] == 'star':
            const = stars_db.get(obj['name'], {}).get('constellation', '')
            if const and const != 'Unknown':
                constellations_present.add(const)
    
    if constellations_present:
        print(f"🌌 Constellations in view: {', '.join(constellations_present)}")
    
    # Display options
    print("\n" + "=" * 70)
    print("DISPLAY OPTIONS:")
    print("1. Raw view (stars only)")
    print("2. Constellation mode (connect the dots)")
    print("3. Return to menu")
    
    choice = input("\nSelect mode: ").strip()
    
    if choice == "1":
        # Raw view
        viewer = EnhancedEyepieceView(width=1200, height=1200)
        viewer.render_eyepiece_view(
            objects_in_view,
            stars_db,
            current_ra,
            current_dec,
            fov,
            constellation_mode=None,
            filename='eyepiece_raw.png'
        )
        print("\n📸 Raw eyepiece view generated!")
        
    elif choice == "2":
        # Constellation mode
        if not constellations_present:
            print("\n⚠️  No recognizable constellations in field of view.")
            return
        
        # Let user choose which constellation to highlight
        const_list = sorted(list(constellations_present))
        print("\nAvailable constellations to highlight:")
        for i, const in enumerate(const_list, 1):
            print(f"{i}. {const}")
        
        try:
            const_choice = int(input("\nSelect constellation number: "))
            if 1 <= const_choice <= len(const_list):
                selected_const = const_list[const_choice - 1]
                
                viewer = EnhancedEyepieceView(width=1200, height=1200)
                viewer.render_eyepiece_view(
                    objects_in_view,
                    stars_db,
                    current_ra,
                    current_dec,
                    fov,
                    constellation_mode=selected_const,
                    filename=f'eyepiece_{selected_const.lower()}.png'
                )
                print(f"\n📸 Constellation mode view generated for {selected_const}!")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input.")
    
    print("=" * 70 + "\n")


def calculate_angular_distance(ra1, dec1, ra2, dec2):
    """Calculate angular distance between two celestial coordinates"""
    ra1_rad = math.radians(ra1)
    dec1_rad = math.radians(dec1)
    ra2_rad = math.radians(ra2)
    dec2_rad = math.radians(dec2)
    
    delta_ra = ra2_rad - ra1_rad
    delta_dec = dec2_rad - dec1_rad
    
    a = math.sin(delta_dec/2)**2 + math.cos(dec1_rad) * math.cos(dec2_rad) * math.sin(delta_ra/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return math.degrees(c)
