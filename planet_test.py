# planet_tracker.py
from skyfield.api import load, wgs84
from datetime import datetime
import math

def calculate_planet_positions(latitude, longitude, location_name="Your Location"):
    """Calculate real-time positions of planets."""
    
    print("Loading planetary ephemeris data...")
    print("(This may take a moment on first run - downloading data files)\n")
    
    # Load ephemeris data
    ts = load.timescale()
    eph = load('de421.bsp')  # Planetary ephemeris
    
    # Set up observer location
    observer = wgs84.latlon(latitude, longitude)
    
    # Get current time
    now = ts.now()
    current_time = datetime.now()
    
    # Define planets to track
    planet_names = {
        'mercury': 'Mercury',
        'venus': 'Venus',
        'mars': 'Mars',
        'jupiter barycenter': 'Jupiter',
        'saturn barycenter': 'Saturn',
        'uranus barycenter': 'Uranus',
        'neptune barycenter': 'Neptune',
        'pluto barycenter': 'Pluto'
    }
    
    print("=" * 70)
    print(f"🪐 PLANET POSITIONS - {location_name} 🪐")
    print("=" * 70)
    print(f"Current time: {current_time.strftime('%I:%M %p, %B %d, %Y')}")
    print(f"Location: Latitude {latitude}°, Longitude {longitude}°")
    print("=" * 70)
    print()
    
    planet_data = []
    
    # Calculate position for each planet
    for planet_key, planet_name in planet_names.items():
        # Get planet object
        earth = eph['earth']
        planet = eph[planet_key]
        
        # Calculate position from Earth
        astrometric = earth.at(now).observe(planet)
        ra, dec, distance = astrometric.radec()
        
        # Calculate altitude and azimuth from observer's location
        topocentric = (earth + observer).at(now).observe(planet)
        alt, az, d = topocentric.apparent().altaz()
        
        # Get RA/Dec in degrees
        ra_degrees = ra._degrees
        dec_degrees = dec.degrees
        altitude = alt.degrees
        azimuth = az.degrees
        distance_au = distance.au
        
        planet_data.append({
            'name': planet_name,
            'ra': ra_degrees,
            'dec': dec_degrees,
            'altitude': altitude,
            'azimuth': azimuth,
            'distance_au': distance_au,
            'visible': altitude > 0  # Above horizon
        })
    
    # Sort by altitude (highest first)
    planet_data.sort(key=lambda x: x['altitude'], reverse=True)
    
    # Display results
    print(f"{'Planet':<12} {'RA (°)':<12} {'Dec (°)':<12} {'Alt (°)':<10} {'Az (°)':<10} {'Dist (AU)':<12} {'Visible'}")
    print("-" * 70)
    
    for planet in planet_data:
        visible_icon = "✓" if planet['visible'] else "✗"
        print(f"{planet['name']:<12} "
              f"{planet['ra']:>10.4f}  "
              f"{planet['dec']:>10.4f}  "
              f"{planet['altitude']:>8.2f}  "
              f"{planet['azimuth']:>8.2f}  "
              f"{planet['distance_au']:>10.2f}  "
              f"{visible_icon}")
    
    print("=" * 70)
    print()
    
    # Show which planets are visible
    visible_planets = [p for p in planet_data if p['visible']]
    
    if visible_planets:
        print(f"🌟 {len(visible_planets)} planet(s) currently visible above the horizon:")
        for planet in visible_planets:
            print(f"  • {planet['name']} at {planet['altitude']:.1f}° altitude")
    else:
        print("⭐ No planets currently visible above the horizon.")
    
    print()
    
    return planet_data

def main():
    print("\n🔭 REAL-TIME PLANET POSITION TRACKER 🔭\n")
    
    # Default to Phoenix, Arizona
    # Change these coordinates to your location
    latitude = 33.4484
    longitude = -112.0740
    location_name = "Phoenix, Arizona"
    
    try:
        planet_data = calculate_planet_positions(latitude, longitude, location_name)
        
        print("\n" + "=" * 70)
        print("NOTES:")
        print("- RA (Right Ascension): 0-360° celestial longitude")
        print("- Dec (Declination): -90 to +90° celestial latitude")
        print("- Alt (Altitude): Height above horizon (negative = below horizon)")
        print("- Az (Azimuth): 0° = North, 90° = East, 180° = South, 270° = West")
        print("- Dist (Distance): Distance from Earth in Astronomical Units (AU)")
        print("=" * 70)
        
    except Exception as e:
        print(f"Error calculating planet positions: {e}")
        print("\nNote: On first run, skyfield downloads ephemeris data files.")
        print("Make sure you have an internet connection.")

if __name__ == "__main__":
    main()