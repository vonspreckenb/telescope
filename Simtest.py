# telescope_simulator.py
import csv
import random
import math

def load_stars(filename):
    """Load stars from CSV with their coordinates."""
    stars = []
    try:
        with open(filename, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get("Ra") and row.get("Dec") and row["Ra"] not in ["N/A", "Unknown"]:
                    stars.append({
                        "name": row["star"],
                        "ra": float(row["Ra"]),
                        "dec": float(row["Dec"]),
                        "magnitude": row["magnitude"],
                        "constellation": row.get("constellation", "Unknown")
                    })
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
    return stars

def calculate_angular_distance(ra1, dec1, ra2, dec2):
    """Calculate angular distance between two celestial coordinates in degrees."""
    # Convert to radians
    ra1_rad = math.radians(ra1)
    dec1_rad = math.radians(dec1)
    ra2_rad = math.radians(ra2)
    dec2_rad = math.radians(dec2)
    
    # Haversine formula for angular distance
    delta_ra = ra2_rad - ra1_rad
    delta_dec = dec2_rad - dec1_rad
    
    a = math.sin(delta_dec/2)**2 + math.cos(dec1_rad) * math.cos(dec2_rad) * math.sin(delta_ra/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return math.degrees(c)

def find_star_by_coordinates(stars, ra, dec, tolerance=2.0):
    """Find the closest star to given coordinates within tolerance (degrees)."""
    closest_star = None
    min_distance = float('inf')
    
    for star in stars:
        distance = calculate_angular_distance(ra, dec, star['ra'], star['dec'])
        if distance < min_distance:
            min_distance = distance
            closest_star = star
    
    if min_distance <= tolerance:
        return closest_star, min_distance
    else:
        return None, min_distance

def display_star_info(star, distance):
    """Display information about the identified star."""
    print("\n" + "=" * 60)
    print("🔭 STAR IDENTIFIED! 🔭")
    print("=" * 60)
    print(f"Star: {star['name']}")
    print(f"Constellation: {star['constellation']}")
    print(f"Magnitude: {star['magnitude']}")
    print(f"Coordinates: RA {star['ra']:.4f}°, Dec {star['dec']:.4f}°")
    print(f"Match accuracy: {distance:.4f}° away from target")
    print("=" * 60 + "\n")

def main():
    print("=" * 60)
    print("🔭 TELESCOPE COORDINATE SIMULATOR 🔭")
    print("=" * 60)
    print("\nLoading star database...\n")
    
    stars = load_stars("stars.csv")
    if not stars:
        print("No stars with coordinates found. Exiting.")
        return
    
    print(f"Loaded {len(stars)} stars with coordinate data.\n")
    
    while True:
        print("\nSimulator Options:")
        print("1. Enter coordinates manually")
        print("2. Point at random star from database")
        print("3. Auto-scan mode (cycles through stars)")
        print("4. Exit simulator")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "1":
            # Manual coordinate entry
            try:
                ra = float(input("Enter Right Ascension (RA in degrees, 0-360): "))
                dec = float(input("Enter Declination (Dec in degrees, -90 to 90): "))
                
                if not (0 <= ra <= 360):
                    print("RA must be between 0 and 360 degrees.")
                    continue
                if not (-90 <= dec <= 90):
                    print("Dec must be between -90 and 90 degrees.")
                    continue
                
                print(f"\n🔭 Telescope pointing to: RA {ra}°, Dec {dec}°")
                print("Searching for matching star...")
                
                star, distance = find_star_by_coordinates(stars, ra, dec)
                
                if star:
                    display_star_info(star, distance)
                else:
                    print(f"\n❌ No star found within 2° of those coordinates.")
                    print(f"Closest star is {distance:.2f}° away.")
                    print("Try different coordinates or increase tolerance.\n")
                    
            except ValueError:
                print("Invalid input. Please enter numeric values.")
        
        elif choice == "2":
            # Random star
            random_star = random.choice(stars)
            # Add small random offset to simulate imperfect pointing
            offset_ra = random.uniform(-0.5, 0.5)
            offset_dec = random.uniform(-0.5, 0.5)
            
            ra = random_star['ra'] + offset_ra
            dec = random_star['dec'] + offset_dec
            
            print(f"\n🔭 Telescope randomly pointing to: RA {ra:.4f}°, Dec {dec:.4f}°")
            print("Searching for matching star...")
            
            star, distance = find_star_by_coordinates(stars, ra, dec)
            
            if star:
                display_star_info(star, distance)
            else:
                print(f"\n❌ No star found (this shouldn't happen!)")
        
        elif choice == "3":
            # Auto-scan mode
            num_scans = input("How many stars to scan? (Enter number or 'all'): ").strip()
            
            if num_scans.lower() == 'all':
                scan_list = stars
            else:
                try:
                    num = int(num_scans)
                    scan_list = random.sample(stars, min(num, len(stars)))
                except ValueError:
                    print("Invalid input.")
                    continue
            
            print(f"\n🔭 Auto-scanning {len(scan_list)} stars...\n")
            
            for i, target_star in enumerate(scan_list, 1):
                # Add small random offset
                offset_ra = random.uniform(-0.3, 0.3)
                offset_dec = random.uniform(-0.3, 0.3)
                
                ra = target_star['ra'] + offset_ra
                dec = target_star['dec'] + offset_dec
                
                print(f"\nScan {i}/{len(scan_list)}: RA {ra:.4f}°, Dec {dec:.4f}°")
                
                star, distance = find_star_by_coordinates(stars, ra, dec)
                
                if star:
                    print(f"  ✓ Found: {star['name']} ({star['constellation']}) - {distance:.4f}° away")
                else:
                    print(f"  ✗ No match found")
                
                if i < len(scan_list):
                    input("  Press Enter to continue to next star...")
            
            print(f"\n✅ Scan complete! Identified {len(scan_list)} positions.\n")
        
        elif choice == "4":
            print("\n🌌 Exiting telescope simulator. Clear skies! 🌌\n")
            break
        
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()