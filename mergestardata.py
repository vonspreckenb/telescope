# merge_star_data.py
import csv

# Read the original stars.csv
stars_data = {}
with open("stars.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        star_name = row["star"].strip()
        stars_data[star_name] = {
            "magnitude": row["magnitude"],
            "temp": row["temp"],
            "type": row["type"],
            "distance": row["distance"],
            "radius": row["radius"]
        }

# Read the starcord.csv with coordinates
coords_data = {}
with open("starcord.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        star_name = row["star"].strip()
        coords_data[star_name] = {
            "Ra": row["RA"],
            "Dec": row["Dec"]
        }

# Merge the data and write to a new file
with open("stars_merged.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    # Write header
    writer.writerow(["star", "magnitude", "temp", "type", "distance", "radius", "Ra", "Dec"])
    
    # Write data for each star
    for star_name in stars_data:
        # Get coordinates if available
        if star_name in coords_data:
            ra = coords_data[star_name]["Ra"]
            dec = coords_data[star_name]["Dec"]
        else:
            ra = "N/A"
            dec = "N/A"
        
        # Write the row
        writer.writerow([
            star_name,
            stars_data[star_name]["magnitude"],
            stars_data[star_name]["temp"],
            stars_data[star_name]["type"],
            stars_data[star_name]["distance"],
            stars_data[star_name]["radius"],
            ra,
            dec
        ])

print("Merge complete! Created stars_merged.csv")
print("Check the file, and if it looks good:")
print("1. Delete (or backup) your old stars.csv")
print("2. Rename stars_merged.csv to stars.csv")