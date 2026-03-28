# starcoord_fetch.py
import csv
import re
from astroquery.simbad import Simbad
import time

# Customize Simbad query
custom_simbad = Simbad()
custom_simbad.reset_votable_fields()
custom_simbad.add_votable_fields('ra', 'dec')

def clean_name(name):
    """Convert concatenated star names to proper SIMBAD format"""
    cleaned = name.replace("*", "").replace("'", "").strip()
    
    # Special cases
    special_cases = {
        "Sun": "Sol",  # SIMBAD doesn't have "Sun"
        "Barnard'sStar": "Barnard's Star",
        "BarnardsStar": "Barnard's Star",
        "BarnardStar": "Barnard's Star",
        "Barnards": "Barnard's Star",
        "Barnard": "Barnard's Star",
        "vanMaanen'sStar": "van Maanen's Star",
        "KapteynsStar": "Kapteyn's Star",
        "ProximaCentauri": "Proxima Centauri",
        "UVCeti": "UV Ceti",
        "YZCeti": "YZ Ceti",
        "ADLeonis": "AD Leonis",
        "EVLacertae": "EV Lacertae",
        "TZArietis": "TZ Arietis",
        "GXAndromedae": "GX Andromedae",
        "GQAndromedae": "GQ Andromedae"
    }
    
    if cleaned in special_cases:
        return special_cases[cleaned]
    
    # Don't split single-word star names
    if cleaned in ["Vega", "Capella", "Spica", "Deneb", "Adhara", 
                   "Shaula", "Atria", "Alhena"]:
        return cleaned
    
    # Split on capital letters
    spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
    
    # Handle catalog names
    spaced = re.sub(r'(HD|BD|Ross|Wolf|Lacaille|Kruger|Struve|L)([0-9])', r'\1 \2', spaced)
    
    # Handle component letters
    spaced = re.sub(r'([a-z])([A-B])$', r'\1 \2', spaced, flags=re.IGNORECASE)
    
    # Fix number+letter combinations like "61Cygni"
    spaced = re.sub(r'(\d)([A-Z])', r'\1 \2', spaced)
    
    return spaced

# Read stars.csv
stars = []
with open("stars.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        stars.append(row["star"])

# Prepare output CSV
with open("starcord.csv", "w", newline="", encoding="utf-8") as out_file:
    writer = csv.writer(out_file)
    writer.writerow(["star", "RA", "Dec"])
    
    for star in stars:
        name_for_query = clean_name(star)
        print(f"Querying: '{star}' as '{name_for_query}'")
        
        try:
            result = custom_simbad.query_object(name_for_query)
            if result is not None and len(result) > 0:
                # USE LOWERCASE FIELD NAMES
                ra = result["ra"][0]
                dec = result["dec"][0]
                print(f"  ✓ Found: RA={ra}, Dec={dec}")
            else:
                ra = "N/A"
                dec = "N/A"
                print(f"  ✗ Not found")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            ra = "N/A"
            dec = "N/A"
        
        writer.writerow([star, ra, dec])
        time.sleep(0.3)  # Be nice to SIMBAD

print("\nDone! Check starcord.csv")