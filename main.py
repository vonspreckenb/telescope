import csv
import math
import time
import os
import threading
import pygame
from datetime import datetime
from skyfield.api import load, wgs84
# Check if optional visualization libraries are available
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Note: matplotlib not available - some visualization features disabled")

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Note: PIL/Pillow not available - some visualization features disabled")
def ra_dec_to_alt_az(ra, dec, lat, lon, lst):
    """Calculates if an object is actually above your horizon."""
    ha = (lst - ra) % 360
    ra_rad, dec_rad, lat_rad, ha_rad = map(math.radians, [ra, dec, lat, ha])
    
    sin_alt = (math.sin(dec_rad) * math.sin(lat_rad) + 
               math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad))
    alt = math.degrees(math.asin(sin_alt))
    return alt, 0 # (Simplified Azimuth for now)

def calculate_moon_position(lat, lon):
    """Calculates the Moon's location for the tonight's visible list."""
    # Simulation: Places moon at a fixed visible spot for testing
    return {"ra": 180.5, "dec": -10.2, "phase": "Waxing Gibbous", "alt": 45.0}

def get_moon_info():
    """Returns general moon facts for the HUD."""
    return {"phase": "Waxing Gibbous", "illumination": "82%", "age": "10 days"}

# ==========================================
# 🔭 SMART TELESCOPE CORE (THREADED)
# ==========================================
class SmartTelescope:
    """Virtual Hardware Layer that runs motors in the background."""
    def __init__(self):
        self.current_ra = 0.0
        self.current_dec = 90.0
        self.target_ra = 0.0
        self.target_dec = 90.0
        self.is_tracking = False
        self.is_slewing = False 
        self.slew_speed = 5.0   # Degrees per second
        self.location = (33.44, -112.07)
    def park(self):
        """Slowly moves the telescope back to the North Pole before shutdown."""
        print("\n🅿️  Parking telescope... returning to Home (0, 90)")
        self.slew_to(0.0, 90.0)
        # Wait for the slew to finish so it doesn't just cut off
        while self.is_slewing:
            time.sleep(0.1)
    def set_location(self, lat, lon):
        self.location = (lat, lon)

    def get_position(self):
        return self.current_ra, self.current_dec

    def slew_to(self, target_ra, target_dec):
        if self.is_slewing:
            return
        self.target_ra, self.target_dec = target_ra, target_dec
        self.is_slewing = True
        # Launch movement in a background thread
        threading.Thread(target=self._move_logic, daemon=True).start()

    def _move_logic(self):
        start_ra, start_dec = self.current_ra, self.current_dec
        steps = 100 
        for i in range(1, steps + 1):
            self.current_ra = start_ra + (self.target_ra - start_ra) * (i/steps)
            self.current_dec = start_dec + (self.target_dec - start_dec) * (i/steps)
            time.sleep(0.02) # 50hz update rate for smooth HUD movement
        self.is_slewing = False
        self.is_tracking = True

# ==========================================
# 📺 TELESCOPE HUD (NIGHT-VISION MODE)
# ==========================================
class TelescopeHUD:
    def __init__(self, telescope, stars):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 480))
        pygame.display.set_caption("Telescope Viewfinder")
        self.telescope = telescope
        self.stars = stars
        self.font = pygame.font.SysFont("monospace", 24, bold=True)
        self.clock = pygame.time.Clock()
        self.running = True

    def start_hud_thread(self):
        """Runs the Pygame window in its own thread."""
        threading.Thread(target=self._hud_loop, daemon=True).start()

    def _hud_loop(self):
        """Continuously update the HUD display."""
        while self.running:
            # IMPORTANT: Process pygame events to keep window responsive
            for event in pygame.event.get():
                if event.type == pygame.QUIT: 
                    self.running = False
                    return  # Exit the loop cleanly
            
            self.screen.fill((10, 0, 0))  # Pitch Black
            cur_ra, cur_dec = self.telescope.get_position()
            
            # Draw HUD Info
            status = "SLEWING" if self.telescope.is_slewing else "TRACKING"
            lines = [
                f"POSITION: {cur_ra:06.2f} / {cur_dec:+06.2f}",
                f"STATUS:   {status}",
                f"OBJECT:   {self.get_nearest_star(cur_ra, cur_dec)}"
            ]
            
            # Render the text lines
            for i, line in enumerate(lines):
                img = self.font.render(line, True, (255, 0, 0))
                self.screen.blit(img, (20, 20 + i*30))
            
            # Simple Crosshair
            pygame.draw.circle(self.screen, (60, 0, 0), (400, 240), 150, 2)
            pygame.draw.line(self.screen, (60, 0, 0), (380, 240), (420, 240), 2)
            pygame.draw.line(self.screen, (60, 0, 0), (400, 220), (400, 260), 2)
            
            pygame.display.flip()
            self.clock.tick(30)  # 30 FPS

    def get_nearest_star(self, ra, dec):
        """Matches your 2,000 star database to current coordinates."""
        for name, data in self.stars.items():
            try:
                s_ra, s_dec = float(data['ra']), float(data['dec'])
                if math.sqrt((ra-s_ra)**2 + (dec-s_dec)**2) < 1.0:
                    return name.upper()
            except: continue
        return "DEEP SPACE"
       
    def check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

# Spectral type descriptions
type_info = {
    "O": "Very hot, blue, very bright",
    "B": "Hot, blue-white, luminous",
    "A": "White, bright, often young stars like Vega",
    "F": "Yellow-white, slightly cooler than A-type",
    "G": "Yellow, like the Sun, medium temperature",
    "K": "Orange, cooler, smaller stars",
    "M": "Red, cool, often red dwarfs"
}

# Constellation information with mythology and facts
constellation_info = {
    "Orion": {
        "description": "The Hunter",
        "mythology": "Orion was a giant huntsman in Greek mythology. According to legend, he boasted that he could hunt any animal on Earth. The goddess Artemis (or Gaia in some versions) sent a scorpion to kill him. Both Orion and the scorpion were placed in the sky, but on opposite sides so they would never meet.",
        "features": "Home to the famous Orion's Belt (three bright stars in a row), the Orion Nebula (a stellar nursery visible to the naked eye), and two brilliant stars: Betelgeuse (red supergiant) and Rigel (blue supergiant).",
        "best_season": "Winter (December - February)"
    },
    "Canis Major": {
        "description": "The Great Dog",
        "mythology": "One of Orion's hunting dogs. In Greek mythology, Canis Major follows Orion across the sky. Some legends say this is Laelaps, the dog that never failed to catch what it was hunting, given as a gift to Europa by Zeus.",
        "features": "Contains Sirius, the brightest star in the night sky, known as the 'Dog Star'. Ancient Egyptians used Sirius's rising to predict the flooding of the Nile River.",
        "best_season": "Winter (January - March)"
    },
    "Ursa Major": {
        "description": "The Great Bear",
        "mythology": "Callisto, a nymph, was transformed into a bear by the jealous goddess Hera (or in some versions, by Zeus to hide her from Hera). Her son Arcas nearly killed her while hunting, but Zeus placed them both in the sky as Ursa Major and Ursa Minor.",
        "features": "Contains the Big Dipper asterism, one of the most recognizable star patterns. The pointer stars (Dubhe and Merak) point toward Polaris, the North Star. Used for navigation for millennia.",
        "best_season": "Spring (March - May), but visible year-round in northern latitudes"
    },
    "Centaurus": {
        "description": "The Centaur",
        "mythology": "Often identified with Chiron, the wise centaur who tutored many Greek heroes including Achilles, Hercules, and Jason. Unlike other centaurs, Chiron was known for his wisdom, kindness, and knowledge of medicine.",
        "features": "Home to Alpha Centauri, our closest stellar neighbor (4.37 light-years away), and Proxima Centauri, the closest individual star. Also contains the spectacular globular cluster Omega Centauri.",
        "best_season": "Spring (April - June), primarily visible from Southern Hemisphere"
    },
    "Lyra": {
        "description": "The Lyre (Harp)",
        "mythology": "The lyre of Orpheus, the legendary musician whose music could charm all living things and even stones. When Orpheus died, Zeus placed his lyre in the heavens. The lyre was created by Hermes from a tortoise shell and given to Apollo.",
        "features": "Dominated by Vega, one of the brightest stars in the sky and part of the Summer Triangle. Vega was the pole star around 12,000 BC and will be again around 13,727 AD due to Earth's precession.",
        "best_season": "Summer (July - September)"
    },
    "Crux": {
        "description": "The Southern Cross",
        "mythology": "Though not from ancient mythology (it was classified in the 16th century), Crux holds deep significance for many cultures. Indigenous Australians saw it as various animals and objects. It's featured on several national flags including Australia and New Zealand.",
        "features": "The smallest of all 88 constellations but one of the most distinctive. Used for navigation in the Southern Hemisphere - the long axis points toward the south celestial pole. Contains the stunning Jewel Box cluster.",
        "best_season": "Autumn/Fall (April - June), visible only from Southern Hemisphere"
    },
    "Scorpius": {
        "description": "The Scorpion",
        "mythology": "The scorpion that killed Orion. In the myth, Orion boasted he could kill any creature, so Gaia sent a scorpion to humble him. They were placed on opposite sides of the sky - when Scorpius rises, Orion sets, eternally fleeing the scorpion.",
        "features": "Contains Antares, a red supergiant whose name means 'rival of Mars' due to its reddish color. The constellation actually looks like a scorpion with its curved tail and stinger clearly visible.",
        "best_season": "Summer (June - August)"
    },
    "Gemini": {
        "description": "The Twins",
        "mythology": "Represents Castor and Pollux, twin half-brothers in Greek mythology. Pollux was immortal (son of Zeus) while Castor was mortal. When Castor died, Pollux begged Zeus to let him share his immortality. Zeus placed them both in the sky together.",
        "features": "The two brightest stars, Castor and Pollux, mark the heads of the twins. Gemini is a zodiac constellation and contains the Gemini Meteor Shower radiant point.",
        "best_season": "Winter (January - March)"
    },
    "Aquila": {
        "description": "The Eagle",
        "mythology": "The eagle that carried Zeus's thunderbolts. In some myths, this is the eagle that abducted Ganymede to serve as cupbearer to the gods. It may also represent the eagle that pecked at Prometheus's liver as punishment.",
        "features": "Contains Altair, one of the closest naked-eye stars at only 17 light-years away. Altair is part of the Summer Triangle asterism along with Vega and Deneb.",
        "best_season": "Summer (July - September)"
    },
    "Taurus": {
        "description": "The Bull",
        "mythology": "Represents the form Zeus took to abduct Europa, a Phoenician princess. Zeus transformed into a beautiful white bull, and when Europa climbed on his back, he carried her across the sea to Crete. The constellation shows only the bull's head and forequarters.",
        "features": "Contains the Pleiades (Seven Sisters) star cluster and the Hyades cluster. The bright red eye of the bull is Aldebaran. The Crab Nebula, remnant of a supernova witnessed in 1054 AD, is also in Taurus.",
        "best_season": "Winter (November - January)"
    },
    "Leo": {
        "description": "The Lion",
        "mythology": "Represents the Nemean Lion, a beast with impenetrable hide killed by Hercules as his first labor. Hercules strangled it with his bare hands since weapons couldn't pierce its skin, then used its own claws to skin it and wore its pelt as armor.",
        "features": "Contains Regulus, a bright blue star marking the lion's heart. The backward question mark shape (the Sickle) forms the lion's head and mane. Leo is a zodiac constellation.",
        "best_season": "Spring (March - May)"
    },
    "Virgo": {
        "description": "The Virgin/Maiden",
        "mythology": "Associated with several goddesses: Demeter (goddess of harvest), her daughter Persephone, or Astraea (goddess of justice). Often depicted holding wheat, represented by the bright star Spica.",
        "features": "Home to the Virgo Cluster, containing over 1,000 galaxies. Spica is one of the brightest stars in the sky. Virgo is the largest zodiac constellation.",
        "best_season": "Spring (April - June)"
    },
    "Cygnus": {
        "description": "The Swan",
        "mythology": "Multiple myths: Zeus disguised as a swan to seduce Leda, or the story of Phaethon whose friend Cygnus dove repeatedly into a river to retrieve his body and was transformed into a swan by Apollo.",
        "features": "Forms the Northern Cross asterism. Contains Deneb, one of the most luminous stars known. The constellation flies along the Milky Way. The 'Great Rift', a dark dust cloud, is visible running through Cygnus.",
        "best_season": "Summer (August - October)"
    },
    "Canis Minor": {
        "description": "The Little Dog",
        "mythology": "Orion's smaller hunting dog, often said to be Maera, the dog of Icarius. In some versions, it represents one of the dogs that hunted with Artemis.",
        "features": "Though small, it contains Procyon, the eighth brightest star in the night sky. Procyon means 'before the dog' because it rises before Sirius, the Dog Star.",
        "best_season": "Winter (February - March)"
    },
    "Boötes": {
        "description": "The Herdsman/Bear Driver",
        "mythology": "Often identified as Arcas (son of Callisto who became Ursa Major), driving the bears around the celestial pole. Others say he's the inventor of the plow, placed in the sky by Demeter for his service to humanity.",
        "features": "Contains Arcturus, the fourth brightest star in the night sky and the brightest in the northern hemisphere. Arcturus means 'bear guardian'. It's a red giant moving rapidly through space.",
        "best_season": "Spring (May - July)"
    },
    "Auriga": {
        "description": "The Charioteer",
        "mythology": "Multiple identifications: Erichthonius, who invented the four-horse chariot, or Myrtilus, the charioteer of King Oenomaus. Often depicted carrying a goat and kids (baby goats).",
        "features": "Contains Capella, the sixth brightest star in the sky, whose name means 'little she-goat'. Home to several spectacular open star clusters.",
        "best_season": "Winter (December - February)"
    },
    "Eridanus": {
        "description": "The River",
        "mythology": "Represents various rivers from mythology - the Nile, the Po, or most commonly the river into which Phaethon fell after losing control of Apollo's sun chariot. It's one of the longest constellations, winding across the sky.",
        "features": "Contains Achernar, whose name means 'end of the river', one of the flattest stars known due to rapid rotation. The constellation represents a celestial river flowing from Orion's foot.",
        "best_season": "Winter (December - January), though it spans a huge area"
    },
    "Piscis Austrinus": {
        "description": "The Southern Fish",
        "mythology": "An ancient constellation, often associated with the Syrian fertility goddess Atargatis (depicted as half-woman, half-fish). In Greek mythology, it may represent the parent of the two fish in Pisces.",
        "features": "Contains Fomalhaut, the 'Solitary One' or 'Autumn Star', one of the brightest stars visible from mid-northern latitudes. Fomalhaut has a debris disk and at least one planet.",
        "best_season": "Autumn/Fall (October - November)"
    },
    "Sagittarius": {
        "description": "The Archer",
        "mythology": "Usually depicted as a centaur archer, identified with Chiron (though Chiron is more commonly Centaurus). Represents a satyr named Crotus, son of Pan, who invented archery and applause.",
        "features": "Points toward the center of our Milky Way galaxy. Contains the Lagoon Nebula and many other deep-sky objects. The 'Teapot' asterism is easily recognizable.",
        "best_season": "Summer (July - August)"
    },
    "Carina": {
        "description": "The Keel (of a ship)",
        "mythology": "Part of the larger constellation Argo Navis, the ship of Jason and the Argonauts, which was later divided into three parts (Carina, Vela, Puppis). The Argonauts sailed to find the Golden Fleece.",
        "features": "Contains Canopus, the second brightest star in the sky, used for spacecraft navigation. Home to the spectacular Carina Nebula and Eta Carinae, a massive unstable star that may go supernova.",
        "best_season": "Summer (February - April), Southern Hemisphere"
    },
    "Perseus": {
        "description": "The Hero",
        "mythology": "Perseus, son of Zeus, famous for slaying Medusa the Gorgon. He used her severed head (which turned viewers to stone) to rescue Andromeda from a sea monster. Often depicted holding Medusa's head.",
        "features": "Contains Algol, the 'Demon Star', an eclipsing binary that changes brightness noticeably. Home to the Double Cluster, two magnificent open clusters visible to the naked eye. The Perseus Meteor Shower radiates from here.",
        "best_season": "Autumn/Fall (November - December)"
    },
    "Pavo": {
        "description": "The Peacock",
        "mythology": "A modern constellation created in the 16th century, not from ancient mythology. The peacock was sacred to Hera in Greek mythology. The eyes on its tail feathers came from the hundred-eyed giant Argus after Hera placed them there.",
        "features": "Contains the bright star Peacock (Alpha Pavonis). Home to NGC 6752, one of the brightest globular clusters in the sky.",
        "best_season": "Winter (July - September), Southern Hemisphere"
    },
    "Triangulum Australe": {
        "description": "The Southern Triangle",
        "mythology": "A modern constellation with no ancient mythology, created by navigators in the 16th century. Its distinctive triangle shape made it useful for navigation in the southern skies.",
        "features": "Small but distinctive constellation. Contains Atria, a bright orange giant. Home to several open clusters.",
        "best_season": "Winter (June - July), Southern Hemisphere"
    },
    "Grus": {
        "description": "The Crane",
        "mythology": "A modern constellation created in the late 16th century, not from ancient mythology. The crane was considered a sacred bird in many cultures, symbolizing vigilance and loyalty.",
        "features": "Contains Alnair, a bright blue star. The constellation actually resembles a bird in flight.",
        "best_season": "Autumn/Fall (September - October), primarily Southern Hemisphere"
    },
    "Vulpecula": {
        "description": "The Little Fox",
        "mythology": "Created in the 17th century by Johannes Hevelius, originally named 'Vulpecula cum Anser' (the little fox with the goose). No ancient mythology associated with it.",
        "features": "Home to the Dumbbell Nebula (M27), one of the brightest planetary nebulae. Also contains several interesting binary star systems.",
        "best_season": "Summer (August - September)"
    },
    "Ophiuchus": {
        "description": "The Serpent Bearer",
        "mythology": "Represents Asclepius, the god of medicine and healing, son of Apollo. He was so skilled he could bring the dead back to life. Zeus killed him with a thunderbolt for defying death, but honored him by placing him in the sky.",
        "features": "Often called the '13th zodiac sign' because the ecliptic passes through it. Contains Barnard's Star, one of the closest stars to Earth. Holds several spectacular globular clusters.",
        "best_season": "Summer (July - August)"
    },
    "Cetus": {
        "description": "The Sea Monster/Whale",
        "mythology": "The sea monster sent by Poseidon to devour Andromeda as punishment for her mother's boasting. Perseus rescued Andromeda by turning the monster to stone using Medusa's head.",
        "features": "Fourth largest constellation. Contains Mira, a famous variable star that changes dramatically in brightness. Also home to Tau Ceti, one of the closest Sun-like stars.",
        "best_season": "Autumn/Fall (November - December)"
    },
    "Indus": {
        "description": "The Indian",
        "mythology": "A modern constellation created in the late 16th century, originally representing a Native American. No ancient mythology associated with it.",
        "features": "Contains Epsilon Indi, one of the closest stars to our solar system. A relatively faint constellation in the southern sky.",
        "best_season": "Spring (September - October), Southern Hemisphere"
    },
    "Draco": {
        "description": "The Dragon",
        "mythology": "Several associations: Ladon, the dragon who guarded the golden apples of the Hesperides, slain by Hercules. Also the dragon killed by Cadmus, or the one thrown at Athena during the war between the gods and Titans.",
        "features": "Long, winding constellation around the north celestial pole. Contains Thuban, which was the pole star around 2700 BC when the Egyptians were building the pyramids. Home to the Cat's Eye Nebula.",
        "best_season": "Summer (July - August), circumpolar in northern latitudes"
    },
    "Andromeda": {
        "description": "The Chained Maiden",
        "mythology": "Princess Andromeda was chained to a rock as a sacrifice to Cetus (sea monster) because her mother Cassiopeia boasted that Andromeda was more beautiful than the Nereids. Perseus rescued her and they married.",
        "features": "Home to the Andromeda Galaxy (M31), the nearest major galaxy to the Milky Way and the most distant object visible to the naked eye at 2.5 million light-years away. Will collide with our galaxy in 4 billion years.",
        "best_season": "Autumn/Fall (October - November)"
    },
    "Monoceros": {
        "description": "The Unicorn",
        "mythology": "A modern constellation created in the 17th century. The unicorn appears in various mythologies but this constellation has no specific mythological story.",
        "features": "Lies on the celestial equator within the Milky Way. Contains the Rosette Nebula and the Christmas Tree Cluster. Home to Plaskett's star, one of the most massive binary star systems known.",
        "best_season": "Winter (January - February)"
    },
    "Pisces": {
        "description": "The Fishes",
        "mythology": "Represents Aphrodite and her son Eros who transformed into fish (or were rescued by fish) to escape the monster Typhon. They tied themselves together with a cord so they wouldn't be separated.",
        "features": "A zodiac constellation, though relatively faint. Contains the vernal equinox point (where the Sun crosses the celestial equator in spring). Home to several interesting galaxies.",
        "best_season": "Autumn/Fall (October - November)"
    },
    "Microscopium": {
        "description": "The Microscope",
        "mythology": "A modern constellation created in the 18th century by Nicolas Louis de Lacaille, honoring scientific instruments. No ancient mythology.",
        "features": "One of the faintest constellations, with no bright stars. A small, inconspicuous constellation in the southern sky.",
        "best_season": "Spring (September), Southern Hemisphere"
    },
    "Pictor": {
        "description": "The Painter's Easel",
        "mythology": "Created in the 18th century by Lacaille, originally named 'Equuleus Pictoris' (the painter's easel). No ancient mythology.",
        "features": "Contains Beta Pictoris, a young star with a prominent debris disk that may be forming planets. One of the best-studied planetary systems.",
        "best_season": "Summer (January - February), Southern Hemisphere"
    },
    "Lacerta": {
        "description": "The Lizard",
        "mythology": "Created in the 17th century by Johannes Hevelius to fill a gap between other constellations. No ancient mythology associated with it.",
        "features": "A small, faint constellation in the northern sky. Contains several interesting variable stars and is crossed by the Milky Way.",
        "best_season": "Autumn/Fall (October)"
    },
    "Aries": {
        "description": "The Ram",
        "mythology": "Represents the golden ram whose fleece became the Golden Fleece sought by Jason and the Argonauts. The ram rescued Phrixus and Helle, carrying them across the sea. Helle fell off, but Phrixus survived and sacrificed the ram to Zeus.",
        "features": "A zodiac constellation, though relatively small and faint. Contains no very bright stars but has several interesting galaxies. The vernal equinox was once located in Aries.",
        "best_season": "Autumn/Fall (November - December)"
    },
    "Sculptor": {
        "description": "The Sculptor's Workshop",
        "mythology": "Created in the 18th century by Lacaille, originally named 'Apparatus Sculptoris'. No ancient mythology - it honors the art of sculpture.",
        "features": "Contains the south galactic pole and several galaxies including the Sculptor Galaxy. A faint constellation in the southern sky.",
        "best_season": "Autumn/Fall (October - November)"
    },
    "Aquarius": {
        "description": "The Water Bearer",
        "mythology": "Often identified with Ganymede, the beautiful youth abducted by Zeus (in the form of an eagle) to serve as cupbearer to the gods. May also represent Deucalion, the Greek Noah who survived a great flood.",
        "features": "A zodiac constellation. Contains the Helix Nebula, one of the closest planetary nebulae to Earth. The radiant point of several meteor showers including the Eta Aquarids and Delta Aquarids.",
        "best_season": "Autumn/Fall (September - October)"
    },
    "Ursa Minor": {
        "description": "The Little Bear",
        "mythology": "Represents Arcas, son of Callisto (Ursa Major), who was also turned into a bear. When Arcas nearly killed his mother while hunting, Zeus placed them both in the sky.",
        "features": "Contains Polaris, the North Star, which marks the north celestial pole and has been used for navigation for centuries. The constellation forms the Little Dipper asterism.",
        "best_season": "Visible year-round from northern latitudes (circumpolar)"
    },
    "Cepheus": {
        "description": "The King",
        "mythology": "King Cepheus of Ethiopia, husband of Cassiopeia and father of Andromeda. He was forced to chain his daughter to a rock to appease Poseidon's wrath after his wife's boastfulness.",
        "features": "Contains Delta Cephei, the prototype Cepheid variable star used to measure cosmic distances. Home to the Garnet Star, one of the largest and reddest stars visible to the naked eye.",
        "best_season": "Autumn/Fall (October - November), circumpolar from northern latitudes"
    },
    "Solar System": {
        "description": "Our Home",
        "mythology": "No constellation - this is the Sun, our home star!",
        "features": "The Sun is a G-type main-sequence star (yellow dwarf) that has been shining for about 4.6 billion years and will continue for another 5 billion years.",
        "best_season": "Visible during daytime!"
    },
    "Unknown": {
        "description": "Unidentified Region",
        "mythology": "This star's constellation information is not available.",
        "features": "No constellation data found.",
        "best_season": "Unknown"
    }
}

def load_planets(filename):
    """Load planet data from CSV file."""
    planets = {}
    try:
        with open(filename, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row["name"].strip()
                planets[name] = {
                    "distance_million_km": row["distance_million_km"],
                    "diameter_km": row["diameter_km"],
                    "mass_earth_masses": row["mass_earth_masses"],
                    "orbital_period_days": row["orbital_period_days"],
                    "rotation_period_hours": row["rotation_period_hours"],
                    "moons": row["moons"],
                    "type": row["type"],
                    "mythology": row["mythology"],
                    "fun_facts": row["fun_facts"]
                }
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
    return planets

def calculate_moon_position(latitude, longitude):
    """Calculate real-time position and phase of the Moon."""
    try:
        from skyfield.api import load
        
        ts = load.timescale()
        eph = load('de421.bsp')
        
        # Set up observer location
        observer = wgs84.latlon(latitude, longitude)
        
        # Get current time
        now = ts.now()
        
        # Get Moon and Sun positions
        earth = eph['earth']
        moon = eph['moon']
        sun = eph['sun']
        
        # Calculate Moon position from Earth
        astrometric = earth.at(now).observe(moon)
        ra, dec, distance = astrometric.radec()
        
        # Calculate altitude and azimuth from observer's location
        topocentric = (earth + observer).at(now).observe(moon)
        alt, az, d = topocentric.apparent().altaz()
        
        # Calculate Moon phase (simplified)
        # Get elongation between Sun and Moon
        sun_pos = earth.at(now).observe(sun)
        sun_ra, sun_dec, _ = sun_pos.radec()
        
        # Calculate elongation in degrees
        elongation = calculate_angular_distance(ra._degrees, dec.degrees, sun_ra._degrees, sun_dec.degrees)
        
        # Determine phase based on elongation
        if elongation < 45:
            phase = "New Moon"
            illumination = 0
        elif 45 <= elongation < 90:
            phase = "Waxing Crescent"
            illumination = 25
        elif 90 <= elongation < 135:
            phase = "First Quarter"
            illumination = 50
        elif 135 <= elongation < 170:
            phase = "Waxing Gibbous"
            illumination = 75
        elif 170 <= elongation < 190:
            phase = "Full Moon"
            illumination = 100
        elif 190 <= elongation < 225:
            phase = "Waning Gibbous"
            illumination = 75
        elif 225 <= elongation < 270:
            phase = "Last Quarter"
            illumination = 50
        elif 270 <= elongation < 315:
            phase = "Waning Crescent"
            illumination = 25
        else:
            phase = "New Moon"
            illumination = 0
        
        moon_data = {
            'ra': ra._degrees,
            'dec': dec.degrees,
            'altitude': alt.degrees,
            'azimuth': az.degrees,
            'distance_km': distance.km,
            'visible': alt.degrees > 0,
            'phase': phase,
            'illumination': illumination
        }
        
        return moon_data
    
    except Exception as e:
        print(f"Error calculating Moon position: {e}")
        return None

def get_moon_info():
    """Get static information about the Moon."""
    return {
        'name': 'The Moon',
        'diameter_km': 3474.8,
        'mass_earth_masses': 0.0123,
        'orbital_period_days': 27.3,
        'rotation_period_hours': 655.7,
        'average_distance_km': 384400,
        'mythology': "The Moon has been revered across all cultures throughout history. In Greek mythology, the Moon is represented by Selene, the Titan goddess who drives her silver chariot across the night sky. The Romans called her Luna. In many cultures, the Moon represents femininity, cycles, and renewal. Ancient civilizations used lunar cycles to create the first calendars. The Moon has inspired countless myths about werewolves, romance, and madness (the word 'lunatic' comes from 'lunar'). Indigenous cultures worldwide have their own moon deities and stories, often associating the Moon with water, tides, and fertility.",
        'fun_facts': "The Moon is Earth's only natural satellite and the fifth largest moon in our solar system. It's gradually moving away from Earth at about 3.8 cm per year. The same side always faces Earth due to tidal locking - we never see the 'dark side.' The Moon's gravity causes ocean tides on Earth. There's no atmosphere, so temperatures range from -173°C in darkness to 127°C in sunlight. The Moon has 'moonquakes' caused by tidal stress from Earth. Footprints left by Apollo astronauts will last millions of years due to no wind or weather. The Moon appears the same size as the Sun in our sky (enabling total solar eclipses) - a cosmic coincidence. The Moon's surface is covered in craters, maria (dark plains), and regolith (lunar dust)."
    }

def calculate_planet_positions(latitude, longitude):
    """Calculate real-time positions of all planets."""
    try:
        # Load ephemeris data
        ts = load.timescale()
        eph = load('de421.bsp')
        
        # Set up observer location
        observer = wgs84.latlon(latitude, longitude)
        
        # Get current time
        now = ts.now()
        
        # Define planets to track
        planet_keys = {
            'mercury': 'Mercury',
            'venus': 'Venus',
            'mars': 'Mars',
            'jupiter barycenter': 'Jupiter',
            'saturn barycenter': 'Saturn',
            'uranus barycenter': 'Uranus',
            'neptune barycenter': 'Neptune',
            'pluto barycenter': 'Pluto'
        }
        
        planet_positions = {}
        
        # Calculate position for each planet
        earth = eph['earth']
        
        for planet_key, planet_name in planet_keys.items():
            planet = eph[planet_key]
            
            # Calculate position from Earth
            astrometric = earth.at(now).observe(planet)
            ra, dec, distance = astrometric.radec()
            
            # Calculate altitude and azimuth from observer's location
            topocentric = (earth + observer).at(now).observe(planet)
            alt, az, d = topocentric.apparent().altaz()
            
            planet_positions[planet_name] = {
                'ra': ra._degrees,
                'dec': dec.degrees,
                'altitude': alt.degrees,
                'azimuth': az.degrees,
                'distance_au': distance.au,
                'visible': alt.degrees > 0
            }
        
        return planet_positions
    
    except Exception as e:
        print(f"Error calculating planet positions: {e}")
        return {}

def ra_dec_to_alt_az(ra, dec, latitude, longitude, lst):
    """Convert RA/Dec to Altitude/Azimuth for visibility calculation."""
    # Convert to radians
    ra_rad = math.radians(ra)
    dec_rad = math.radians(dec)
    lat_rad = math.radians(latitude)
    lst_rad = math.radians(lst)
    
    # Hour angle
    ha = lst_rad - ra_rad
    
    # Calculate altitude
    sin_alt = math.sin(dec_rad) * math.sin(lat_rad) + math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha)
    alt = math.degrees(math.asin(sin_alt))
    
    # Calculate azimuth
    cos_az = (math.sin(dec_rad) - math.sin(lat_rad) * sin_alt) / (math.cos(lat_rad) * math.cos(math.radians(alt)))
    # Clamp to [-1, 1] to avoid math domain errors
    cos_az = max(-1, min(1, cos_az))
    az = math.degrees(math.acos(cos_az))
    
    if math.sin(ha) > 0:
        az = 360 - az
    
    return alt, az

def calculate_lst(longitude, utc_time):
    """Calculate Local Sidereal Time."""
    # Simplified LST calculation
    # J2000 epoch: January 1, 2000, 12:00 UT
    j2000 = datetime(2000, 1, 1, 12, 0, 0)
    
    # Days since J2000
    delta = utc_time - j2000
    days = delta.total_seconds() / 86400.0
    
    # Greenwich Sidereal Time at 0h UT
    gst = 100.46 + 0.985647 * days + 15 * utc_time.hour + 0.25 * utc_time.minute
    
    # Local Sidereal Time
    lst = (gst + longitude) % 360
    
    return lst

def get_visible_stars(stars, latitude, longitude, min_altitude=10):
    """Get stars currently visible above the horizon."""
    current_time = datetime.utcnow()
    lst = calculate_lst(longitude, current_time)
    
    visible = []
    for name, data in stars.items():
        # Skip stars without coordinates
        if data['ra'] in ["Unknown", "N/A"] or data['dec'] in ["Unknown", "N/A"]:
            continue
        
        try:
            ra = float(data['ra'])
            dec = float(data['dec'])
            mag = float(data['magnitude'])
            
            # Calculate altitude and azimuth
            alt, az = ra_dec_to_alt_az(ra, dec, latitude, longitude, lst)
            
            # Only include stars above minimum altitude
            if alt >= min_altitude:
                visible.append({
                    'name': name,
                    'data': data,
                    'altitude': alt,
                    'azimuth': az,
                    'magnitude': mag
                })
        except (ValueError, TypeError):
            continue
    
    # Sort by altitude (highest first) then by magnitude (brightest first)
    visible.sort(key=lambda x: (-x['altitude'], x['magnitude']))
    
    return visible

def display_visibility_info(stars, planets, planet_positions, observer_location, moon_position=None):
    """Display tonight's visible stars, planets, and Moon."""
    latitude, longitude, location_name = observer_location
    
    current_time = datetime.now()
    
    print("\n" + "=" * 70)
    print(f"🌙 TONIGHT'S SKY - {location_name} 🌙")
    print("=" * 70)
    print(f"Current time: {current_time.strftime('%I:%M %p')}")
    print(f"Location: Latitude {latitude}°, Longitude {longitude}°")
    
    # Determine if it's daytime or nighttime
    hour = current_time.hour
    if 6 <= hour < 18:
        print("Sky condition: ☀️ DAYTIME - Stars not visible")
        print("Come back after sunset for stargazing!")
        print("=" * 70 + "\n")
        return [], [], None
    else:
        print("Sky condition: 🌃 NIGHTTIME - Good for stargazing!")
    
    # Show Moon if available
    if moon_position and moon_position['visible'] and moon_position['altitude'] > 15:
        print(f"\n🌙 THE MOON")
        print("=" * 70)
        print(f"Phase: {moon_position['phase']} ({moon_position['illumination']}% illuminated)")
        print(f"Altitude: {moon_position['altitude']:.1f}°")
        print(f"Distance: {moon_position['distance_km']:,.0f} km")
    
    # Get visible planets
    visible_planets = []
    if planet_positions:
        for name, pos in planet_positions.items():
            if pos['visible'] and pos['altitude'] > 15:
                planet_data = planets.get(name, {})
                visible_planets.append({
                    'name': name,
                    'data': planet_data,
                    'altitude': pos['altitude'],
                    'azimuth': pos['azimuth'],
                    'ra': pos['ra'],
                    'dec': pos['dec'],
                    'distance_au': pos['distance_au']
                })
        visible_planets.sort(key=lambda x: x['altitude'], reverse=True)
    
    # Get visible stars
    visible_stars = get_visible_stars(stars, latitude, longitude, min_altitude=15)
    
    # Display planets first
    if visible_planets:
        print(f"\n🪐 VISIBLE PLANETS ({len(visible_planets)} above horizon)")
        print("=" * 70)
        print(f"{'Planet':<15} {'Type':<18} {'Alt':<8} {'Distance (AU)'}")
        print("-" * 70)
        for planet in visible_planets:
            ptype = planet['data'].get('type', 'Unknown')
            print(f"{planet['name']:<15} {ptype:<18} {planet['altitude']:>6.1f}° {planet['distance_au']:>8.2f}")
    
    # Display stars
    if visible_stars:
        print(f"\n✨ VISIBLE STARS ({len(visible_stars)} brightest shown)")
        print("=" * 70)
        display_count = min(20, len(visible_stars))
        print(f"{'#':<4} {'Star':<18} {'Constellation':<20} {'Alt':<6} {'Mag':<6}")
        print("-" * 70)
        
        for i, star in enumerate(visible_stars[:display_count], 1):
            name = star['name'].title()
            const = star['data']['constellation']
            alt = star['altitude']
            mag = star['magnitude']
            print(f"{i:<4} {name:<18} {const:<20} {alt:>5.1f}° {mag:>6.1f}")
    
    print("=" * 70 + "\n")
    
    return visible_planets, visible_stars, moon_position

def simulate_goto(telescope_hw, star_name, ra, dec):
    """
    Commands the SmartTelescope class to move.
    Replaces the old text-only function.
    """
    print(f"\n{'=' * 60}")
    print(f"🔭 INITIATING GOTO SEQUENCE: {star_name.upper()}")
    print(f"{'=' * 60}")
    
    # Command the hardware
    telescope_hw.slew_to(float(ra), float(dec))
    
    print(f"\n{'=' * 60}")
    print(f"🎯 TELESCOPE LOCKED ON: {star_name.upper()}")
    print(f"{'=' * 60}\n")
    time.sleep(0.5)

def telescope_view(stars, planets, planet_positions, observer_location, moon_position, telescope_hw):
    """
    Display what's currently visible through the eyepiece.
    Now pulls coordinates automatically from the SmartTelescope hardware!
    """
    print("\n" + "=" * 70)
    print("🔭 TELESCOPE EYEPIECE VIEW 🔭")
    print("=" * 70)
    
    # AUTOMATICALLY get position from the "Hardware"
    current_ra, current_dec = telescope_hw.get_position()
    
    print(f"Current Pointing: RA {current_ra:.2f}°, Dec {current_dec:.2f}°")
    
    # Field of view (typical telescope eyepiece is 0.8 degree)
    fov = 0.8 
    
    print(f"Scanning field of view ({fov*2:.1f}° diameter)...")
    print("-" * 70)
    
    objects_in_view = []
    
    # 1. Check Moon
    if moon_position and moon_position.get('visible'):
        dist = calculate_angular_distance(current_ra, current_dec, moon_position['ra'], moon_position['dec'])
        if dist <= fov:
            objects_in_view.append({'name': 'The Moon', 'type': 'moon', 'distance_deg': dist, 'mag': -12.6})

    # 2. Check Planets
    if planet_positions:
        for name, pos in planet_positions.items():
            dist = calculate_angular_distance(current_ra, current_dec, pos['ra'], pos['dec'])
            if dist <= fov:
                objects_in_view.append({'name': name, 'type': 'planet', 'distance_deg': dist, 'mag': -2.0})

    # 3. Check Stars
    for name, data in stars.items():
        if data['ra'] == "Unknown": continue
        try:
            dist = calculate_angular_distance(current_ra, current_dec, float(data['ra']), float(data['dec']))
            if dist <= fov:
                objects_in_view.append({'name': name, 'type': 'star', 'distance_deg': dist, 'mag': float(data.get('magnitude', 6))})
        except: continue

    # Display Logic
    if not objects_in_view:
        print("❌ Dark sky. No major objects in field of view.")
        print("   Try using 'GoTo' to find a bright star!")
    else:
        objects_in_view.sort(key=lambda x: x['distance_deg'])
        print(f"{'Object':<20} {'Type':<10} {'Dist from Center':<20}")
        print("-" * 50)
        for obj in objects_in_view:
            center_status = "🎯 BULLSEYE" if obj['distance_deg'] < 0.1 else f"{obj['distance_deg']:.2f}° away"
            print(f"{obj['name'].title():<20} {obj['type']:<10} {center_status}")
            
    print("=" * 70 + "\n")
    
    # Visual map generation (Optional - keeps your existing logic)
    if (MATPLOTLIB_AVAILABLE or PIL_AVAILABLE) and objects_in_view:
        ask = input("Render visual map? (y/n): ")
        if ask.lower() == 'y':
            if MATPLOTLIB_AVAILABLE:
                create_telescope_view_image(objects_in_view, current_ra, current_dec, fov)
            elif PIL_AVAILABLE:
                create_telescope_view_image_pil(objects_in_view, current_ra, current_dec, fov)

def show_planet_image(planet_name, planet_data):
    """Create and display an informational image of a planet."""
    print(f"\n🖼️  Creating image information card for {planet_name}...")
    
    if not PIL_AVAILABLE:
        print("⚠️  PIL/Pillow library not available. Showing text information instead.")
        print(f"\n{'=' * 70}")
        print(f"🪐 {planet_name.upper()} - VISUAL INFORMATION 🪐")
        print(f"{'=' * 70}")
        print(f"Type: {planet_data.get('type', 'Unknown')}")
        print(f"Distance from Sun: {planet_data.get('distance_million_km', 'Unknown')} million km")
        print(f"Diameter: {planet_data.get('diameter_km', 'Unknown')} km")
        print(f"\n💡 To see actual images of {planet_name}, visit:")
        print(f"   https://solarsystem.nasa.gov/planets/{planet_name.lower()}/overview/")
        print(f"   or search for '{planet_name} NASA images'")
        print(f"{'=' * 70}\n")
        return False
    
    try:
        # Create image
        width, height = 800, 600
        img = Image.new('RGB', (width, height), color='#0a0e27')  # Dark space blue
        draw = ImageDraw.Draw(img)
        
        # Try to use a nice font, fallback to default
        try:
            title_font = ImageFont.truetype("arial.ttf", 48)
            header_font = ImageFont.truetype("arial.ttf", 32)
            text_font = ImageFont.truetype("arial.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Draw title
        title = f"{planet_name.upper()}"
        draw.text((width//2, 50), title, fill='#ffffff', font=title_font, anchor='mt')
        
        # Draw planet type
        planet_type = planet_data.get('type', 'Unknown')
        draw.text((width//2, 120), planet_type, fill='#4a9eff', font=header_font, anchor='mt')
        
        # Draw information
        y_pos = 200
        info_lines = [
            f"Distance from Sun: {planet_data.get('distance_million_km', 'Unknown')} million km",
            f"Diameter: {planet_data.get('diameter_km', 'Unknown')} km",
            f"Mass: {planet_data.get('mass_earth_masses', 'Unknown')} Earth masses",
            f"Orbital Period: {planet_data.get('orbital_period_days', 'Unknown')} days",
            f"Day Length: {planet_data.get('rotation_period_hours', 'Unknown')} hours",
            f"Moons: {planet_data.get('moons', 'Unknown')}"
        ]
        
        for line in info_lines:
            draw.text((50, y_pos), line, fill='#ffffff', font=text_font)
            y_pos += 50
        
        # Add note at bottom
        note = "Visit NASA.gov for actual planet images"
        draw.text((width//2, height - 50), note, fill='#888888', font=text_font, anchor='mt')
        
        # Save image
        filename = f"{planet_name.lower()}_info.png"
        img.save(filename)
        print(f"✓ Image information card created successfully!")
        print(f"📸 Image saved as: {filename}")
        print(f"\n💡 Tip: The image has been saved to your workspace.")
        print(f"   For actual photos, visit: https://solarsystem.nasa.gov/planets/{planet_name.lower()}/overview/")
        return True
    except Exception as e:
        print(f"⚠️  Could not create image: {e}")
        print("Showing text information instead.")
        print(f"\n💡 To see actual images of {planet_name}, visit NASA's website.")
        return False

def show_star_image(star_name, star_data):
    """Create and display an informational image of a star."""
    print(f"\n🖼️  Creating image information card for {star_name}...")
    
    if not PIL_AVAILABLE:
        print("⚠️  PIL/Pillow library not available. Showing text information instead.")
        print(f"\n{'=' * 70}")
        print(f"✨ {star_name.upper()} - VISUAL INFORMATION ✨")
        print(f"{'=' * 70}")
        print(f"Constellation: {star_data.get('constellation', 'Unknown')}")
        print(f"Magnitude: {star_data.get('magnitude', 'Unknown')}")
        print(f"Temperature: {star_data.get('temperature', 'Unknown')} K")
        print(f"Distance: {star_data.get('distance', 'Unknown')} ly")
        print(f"\n💡 To see actual images of {star_name}, visit:")
        print(f"   https://en.wikipedia.org/wiki/{star_name.replace(' ', '_')}")
        print(f"   or search for '{star_name} star images'")
        print(f"{'=' * 70}\n")
        return False
    
    try:
        # Get star characteristics
        spectral_type = star_data.get('type', 'G').upper()
        temperature = star_data.get('temperature', 'Unknown')
        constellation = star_data.get('constellation', 'Unknown')
        magnitude = star_data.get('magnitude', 'Unknown')
        distance = star_data.get('distance', 'Unknown')
        
        # Create color based on spectral type
        color_map = {
            'O': '#4a9eff',  # Blue-white
            'B': '#6bb6ff',  # Blue-white
            'A': '#ffffff',  # White
            'F': '#fff9e6',  # Yellow-white
            'G': '#ffeb3b',  # Yellow
            'K': '#ff9800',  # Orange
            'M': '#ff5722'   # Red
        }
        star_color = color_map.get(spectral_type, '#ffffff')
        
        # Create image
        width, height = 800, 600
        img = Image.new('RGB', (width, height), color='#0a0e27')  # Dark space blue
        draw = ImageDraw.Draw(img)
        
        # Try to use a nice font, fallback to default
        try:
            title_font = ImageFont.truetype("arial.ttf", 48)
            header_font = ImageFont.truetype("arial.ttf", 32)
            text_font = ImageFont.truetype("arial.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Draw title
        title = f"{star_name.upper()}"
        draw.text((width//2, 50), title, fill=star_color, font=title_font, anchor='mt')
        
        # Draw a star symbol
        center_x, center_y = width//2, 200
        star_size = 30
        # Simple 5-pointed star
        points = []
        for i in range(10):
            angle = (i * math.pi) / 5
            r = star_size if i % 2 == 0 else star_size // 2
            x = center_x + r * math.cos(angle - math.pi/2)
            y = center_y + r * math.sin(angle - math.pi/2)
            points.append((x, y))
        if len(points) >= 3:
            draw.polygon(points, fill=star_color, outline=star_color)
        
        # Draw constellation
        const_text = f"Constellation: {constellation}"
        draw.text((width//2, 280), const_text, fill='#4a9eff', font=header_font, anchor='mt')
        
        # Draw information
        y_pos = 340
        info_lines = [
            f"Spectral Type: {spectral_type}",
            f"Magnitude: {magnitude}",
            f"Temperature: {temperature} K",
            f"Distance: {distance} ly",
            f"Radius: {star_data.get('radius', 'Unknown')} x Sun"
        ]
        
        for line in info_lines:
            draw.text((50, y_pos), line, fill='#ffffff', font=text_font)
            y_pos += 40
        
        # Add note at bottom
        note = "Visit Wikipedia or NASA for actual star images"
        draw.text((width//2, height - 50), note, fill='#888888', font=text_font, anchor='mt')
        
        # Save image
        safe_name = star_name.lower().replace(' ', '_').replace('/', '_')
        filename = f"{safe_name}_info.png"
        img.save(filename)
        print(f"✓ Image information card created successfully!")
        print(f"📸 Image saved as: {filename}")
        print(f"\n💡 Tip: The image has been saved to your workspace.")
        print(f"   For actual photos, search for '{star_name} star images' online.")
        return True
    except Exception as e:
        print(f"⚠️  Could not create image: {e}")
        print("Showing text information instead.")
        print(f"\n💡 To see actual images of {star_name}, search online or visit Wikipedia.")
        return False

def list_bright_stars(stars, limit=20):
    """Get a list of the brightest stars for quick selection."""
    star_list = []
    for name, data in stars.items():
        try:
            mag = float(data['magnitude'])
            if data['ra'] not in ["Unknown", "N/A"]:
                star_list.append((name, data, mag))
        except (ValueError, TypeError):
            continue
    
    # Sort by magnitude (lower = brighter)
    star_list.sort(key=lambda x: x[2])
    return star_list[:limit]

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

def find_object_by_coordinates(stars, planets, planet_positions, ra, dec, moon_position=None, tolerance=2.0):
    """Find the closest star, planet, or Moon to given coordinates within tolerance (degrees)."""
    closest_object = None
    closest_name = None
    object_type = None
    min_distance = float('inf')
    
    # Check Moon first if available
    if moon_position and moon_position['visible']:
        moon_ra = moon_position['ra']
        moon_dec = moon_position['dec']
        
        distance = calculate_angular_distance(ra, dec, moon_ra, moon_dec)
        if distance < min_distance:
            min_distance = distance
            closest_object = moon_position
            closest_name = "Moon"
            object_type = 'moon'
    
    # Then check planets
    if planet_positions:
        for planet_name, pos in planet_positions.items():
            planet_ra = pos['ra']
            planet_dec = pos['dec']
            
            distance = calculate_angular_distance(ra, dec, planet_ra, planet_dec)
            if distance < min_distance:
                min_distance = distance
                closest_object = {
                    'position': pos,
                    'data': planets.get(planet_name, {})
                }
                closest_name = planet_name
                object_type = 'planet'
    
    # Then check stars
    for star_name, star_data in stars.items():
        # Skip stars without coordinates
        if star_data['ra'] in ["Unknown", "N/A"] or star_data['dec'] in ["Unknown", "N/A"]:
            continue
        
        try:
            star_ra = float(star_data['ra'])
            star_dec = float(star_data['dec'])
            
            distance = calculate_angular_distance(ra, dec, star_ra, star_dec)
            if distance < min_distance:
                min_distance = distance
                closest_object = star_data
                closest_name = star_name
                object_type = 'star'
        except (ValueError, TypeError):
            continue
    
    if min_distance <= tolerance:
        return closest_name, closest_object, object_type, min_distance
    else:
        return None, None, None, min_distance

def find_star_by_coordinates(stars, ra, dec, tolerance=2.0):
    """Find the closest star to given coordinates within tolerance (degrees)."""
    closest_star = None
    closest_star_name = None
    min_distance = float('inf')
    
    for star_name, star_data in stars.items():
        # Skip stars without coordinates
        if star_data['ra'] in ["Unknown", "N/A"] or star_data['dec'] in ["Unknown", "N/A"]:
            continue
        
        try:
            star_ra = float(star_data['ra'])
            star_dec = float(star_data['dec'])
            
            distance = calculate_angular_distance(ra, dec, star_ra, star_dec)
            if distance < min_distance:
                min_distance = distance
                closest_star = star_data
                closest_star_name = star_name
        except (ValueError, TypeError):
            continue
    
    if min_distance <= tolerance:
        return closest_star_name, closest_star, min_distance
    else:
        return None, None, min_distance

def load_stars(filename):
    """Load stars from a CSV file into a dictionary."""
    stars = {}
    try:
        with open(filename, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
            for row in reader:
                name = row["star"].strip().lower()
                stars[name] = {
                    "magnitude": row["magnitude"],
                    "temperature": row["temp"],
                    "type": row.get("type", "Unknown"),
                    "distance": row.get("distance", "Unknown"),
                    "radius": row.get("radius", "Unknown"),
                    "ra": row.get("Ra", "Unknown"),
                    "dec": row.get("Dec", "Unknown"),
                    "constellation": row.get("constellation", "Unknown")
                }
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
    return stars

def get_constellations_from_stars(stars):
    """Get unique constellation names from loaded stars."""
    constellations = set()
    for star_data in stars.values():
        const = star_data.get("constellation", "Unknown")
        if const != "Unknown":
            constellations.add(const)
    return sorted(constellations)

def get_stars_in_constellation(stars, constellation_name):
    """Get all stars in a specific constellation."""
    stars_in_const = []
    for star_name, star_data in stars.items():
        if star_data.get("constellation") == constellation_name:
            stars_in_const.append((star_name.title(), star_data))
    return sorted(stars_in_const, key=lambda x: float(x[1]["magnitude"]) if x[1]["magnitude"] not in ["N/A", "Unknown"] else 999)

def create_telescope_view_image(objects_in_view, center_ra, center_dec, fov):
    """Create a visual representation of the telescope view using matplotlib."""
    if not MATPLOTLIB_AVAILABLE:
        return
    
    try:
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_facecolor('black')
        fig.patch.set_facecolor('black')
        
        # Plot stars/objects
        for obj in objects_in_view:
            # Convert angular distance to x,y coordinates
            distance = obj['distance_deg']
            # Simple projection: assume small field, use linear approximation
            angle = math.radians(0)  # Simplified - would need proper projection
            x = distance * math.cos(angle)
            y = distance * math.sin(angle)
            
            mag = obj.get('magnitude', 5.0)
            if not isinstance(mag, (int, float)):
                mag = 5.0
            
            # Size based on magnitude (brighter = larger)
            size = max(10, 100 / (mag + 5))
            
            # Color based on type
            if obj['type'] == 'star':
                color = 'white'
            elif obj['type'] == 'planet':
                color = 'yellow'
            elif obj['type'] == 'moon':
                color = 'lightblue'
            else:
                color = 'gray'
            
            ax.scatter(x, y, s=size, c=color, alpha=0.8, edgecolors='none')
            
            # Label if bright enough
            if mag < 3:
                ax.annotate(obj['name'].title(), (x, y), 
                           xytext=(5, 5), textcoords='offset points',
                           color='white', fontsize=8)
        
        # Add crosshair at center
        ax.axhline(y=0, color='green', linestyle='--', linewidth=1, alpha=0.5)
        ax.axvline(x=0, color='green', linestyle='--', linewidth=1, alpha=0.5)
        ax.scatter(0, 0, s=50, c='green', marker='+', linewidths=2)
        
        # Set limits
        ax.set_xlim(-fov, fov)
        ax.set_ylim(-fov, fov)
        ax.set_aspect('equal')
        ax.set_xlabel('RA offset (degrees)', color='white')
        ax.set_ylabel('Dec offset (degrees)', color='white')
        ax.tick_params(colors='white')
        
        plt.title(f'Telescope View - RA {center_ra:.2f}°, Dec {center_dec:.2f}°', 
                 color='white', fontsize=12)
        
        filename = 'telescope_view.png'
        plt.savefig(filename, facecolor='black', dpi=150)
        print(f"\n✓ Visual map saved as: {filename}")
        plt.close()
        
    except Exception as e:
        print(f"⚠️  Could not create visual: {e}")

def create_telescope_view_image_pil(objects_in_view, center_ra, center_dec, fov):
    """Create a visual representation using PIL."""
    if not PIL_AVAILABLE:
        return
    
    try:
        width, height = 800, 800
        img = Image.new('RGB', (width, height), color='#000000')
        draw = ImageDraw.Draw(img)
        
        center_x, center_y = width // 2, height // 2
        scale = min(width, height) / (fov * 2)  # Scale to fit FOV
        
        # Draw crosshair
        draw.line([(center_x - 20, center_y), (center_x + 20, center_y)], 
                 fill='#00ff00', width=2)
        draw.line([(center_x, center_y - 20), (center_x, center_y + 20)], 
                 fill='#00ff00', width=2)
        draw.ellipse([center_x - 5, center_y - 5, center_x + 5, center_y + 5], 
                    fill='#00ff00')
        
        # Draw objects
        for obj in objects_in_view:
            distance = obj['distance_deg']
            # Simplified circular projection
            angle = 0  # Would need proper projection
            x = center_x + distance * scale * math.cos(angle)
            y = center_y + distance * scale * math.sin(angle)
            
            mag = obj.get('magnitude', 5.0)
            if not isinstance(mag, (int, float)):
                mag = 5.0
            
            # Size based on magnitude
            size = max(2, int(20 / (mag + 5)))
            
            # Color based on type
            if obj['type'] == 'star':
                color = '#ffffff'
            elif obj['type'] == 'planet':
                color = '#ffff00'
            elif obj['type'] == 'moon':
                color = '#add8e6'
            else:
                color = '#888888'
            
            draw.ellipse([x - size, y - size, x + size, y + size], 
                        fill=color, outline=color)
            
            # Label bright objects
            if mag < 3:
                try:
                    font = ImageFont.truetype("arial.ttf", 12)
                except:
                    font = ImageFont.load_default()
                draw.text((x + size + 5, y - 5), obj['name'].title()[:15], 
                         fill='#ffffff', font=font)
        
        filename = 'telescope_view.png'
        img.save(filename)
        print(f"\n✓ Visual map saved as: {filename}")
        
    except Exception as e:
        print(f"⚠️  Could not create visual: {e}")

def learn_about_menu(stars, planets, planet_positions, observer_location):
    """Educational menu for learning about celestial objects."""
    while True:
        print("\n" + "=" * 70)
        print("📖 LEARN ABOUT CELESTIAL OBJECTS 📖")
        print("=" * 70)
        print("1. Visible stars tonight")
        print("2. Visible planets tonight")
        print("3. All stars (browse by constellation or search)")
        print("4. All planets")
        print("5. Return to main menu")
        
        learn_choice = input("\nWhat would you like to learn about? ").strip()
        
        if learn_choice == "1":
            # Learn about visible stars
            latitude, longitude, _ = observer_location
            visible_stars = get_visible_stars(stars, latitude, longitude, min_altitude=15)
            
            if not visible_stars:
                print("\nNo bright stars currently visible above 15° altitude.\n")
                continue
            
            print(f"\n✨ VISIBLE STARS TONIGHT ({len(visible_stars)} above horizon)")
            print("=" * 70)
            display_count = min(25, len(visible_stars))
            
            for i, star in enumerate(visible_stars[:display_count], 1):
                name = star['name'].title()
                const = star['data']['constellation']
                mag = star['magnitude']
                print(f"{i:2}. {name:<20} {const:<20} Mag: {mag:>6.1f}")
            
            try:
                selection = int(input(f"\nSelect a star to learn about (1-{display_count}): "))
                if 1 <= selection <= display_count:
                    selected = visible_stars[selection - 1]
                    star_name = selected['name']
                    star_data = selected['data']
                    
                    print(f"\n{'=' * 70}")
                    print(f"⭐ {star_name.upper()} ⭐")
                    print(f"{'=' * 70}")
                    print(f"Constellation: {star_data['constellation']}")
                    print(f"Magnitude: {star_data['magnitude']}")
                    print(f"Temperature: {star_data['temperature']} K")
                    print(f"Distance: {star_data['distance']} ly")
                    print(f"Radius: {star_data['radius']} times bigger than our sun")
                    print(f"Coordinates: RA {star_data['ra']}°, Dec {star_data['dec']}°")
                    print(f"Current altitude: {selected['altitude']:.1f}°")
                    
                    spectral_type = star_data['type'].upper()
                    if spectral_type in type_info:
                        print(f"\nSpectral Type: {spectral_type}")
                        print(f"Type info: {type_info[spectral_type]}")
                    
                    # Show constellation info
                    const_name = star_data['constellation']
                    if const_name in constellation_info:
                        const_data = constellation_info[const_name]
                        print(f"\n🌌 CONSTELLATION: {const_name}")
                        print(f"{const_data['description']}")
                        print(f"\n📖 Mythology: {const_data['mythology'][:300]}...")
                    
                    print(f"{'=' * 70}\n")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input.")
        
        elif learn_choice == "2":
            # Learn about visible planets
            visible_planets = []
            if planet_positions:
                for name, pos in planet_positions.items():
                    if pos['visible'] and pos['altitude'] > 15:
                        planet_data = planets.get(name, {})
                        visible_planets.append({
                            'name': name,
                            'data': planet_data,
                            'altitude': pos['altitude'],
                            'distance_au': pos['distance_au']
                        })
                visible_planets.sort(key=lambda x: x['altitude'], reverse=True)
            
            if not visible_planets:
                print("\nNo planets currently visible above 15° altitude.\n")
                continue
            
            print(f"\n🪐 VISIBLE PLANETS TONIGHT ({len(visible_planets)} above horizon)")
            print("=" * 70)
            
            for i, planet in enumerate(visible_planets, 1):
                ptype = planet['data'].get('type', 'Unknown')
                print(f"{i}. {planet['name']:<15} {ptype:<20} Alt: {planet['altitude']:>5.1f}°")
            
            # Ask if they want to look at one
            look_choice = input("\nWould you like to look at one of these planets? (y/n): ").strip().lower()
            
            if look_choice == 'y':
                try:
                    selection = int(input(f"Select a planet (1-{len(visible_planets)}): "))
                    if 1 <= selection <= len(visible_planets):
                        selected = visible_planets[selection - 1]
                        planet_name = selected['name']
                        planet_data = selected['data']
                        
                        print(f"\n{'=' * 70}")
                        print(f"🪐 {planet_name.upper()} 🪐")
                        print(f"{'=' * 70}")
                        print(f"Type: {planet_data.get('type', 'Unknown')}")
                        print(f"Distance from Sun: {planet_data.get('distance_million_km', 'Unknown')} million km")
                        print(f"Diameter: {planet_data.get('diameter_km', 'Unknown')} km")
                        print(f"Mass: {planet_data.get('mass_earth_masses', 'Unknown')} Earth masses")
                        print(f"Orbital Period: {planet_data.get('orbital_period_days', 'Unknown')} days")
                        print(f"Day Length: {planet_data.get('rotation_period_hours', 'Unknown')} hours")
                        print(f"Known Moons: {planet_data.get('moons', 'Unknown')}")
                        print(f"Current altitude: {selected['altitude']:.1f}°")
                        print(f"Distance from Earth: {selected['distance_au']:.2f} AU")
                        
                        print(f"\n📖 MYTHOLOGY:")
                        print(f"{planet_data.get('mythology', 'No mythology available.')}")
                        print(f"\n⭐ FUN FACTS:")
                        print(f"{planet_data.get('fun_facts', 'No facts available.')}")
                        print(f"{'=' * 70}\n")
                    else:
                        print("Invalid selection.\n")
                except ValueError:
                    print("Invalid input.\n")
            else:
                print()
        
        elif learn_choice == "3":
            # Learn about all stars (browse by constellation)
            print("\nHow would you like to browse stars?")
            print("1. By constellation")
            print("2. Search by name")
            
            browse_choice = input("\nEnter your choice: ").strip()
            
            if browse_choice == "1":
                # Browse by constellation (existing constellation browser)
                available_constellations = get_constellations_from_stars(stars)
                
                print("\n✨ Available Constellations ✨")
                print("=" * 50)
                for i, const in enumerate(available_constellations, 1):
                    print(f"{i}. {const}")
                
                try:
                    const_choice = int(input("\nSelect constellation number: "))
                    if 1 <= const_choice <= len(available_constellations):
                        selected_constellation = available_constellations[const_choice - 1]
                        
                        if selected_constellation in constellation_info:
                            info = constellation_info[selected_constellation]
                            print(f"\n{'=' * 60}")
                            print(f"🌌 {selected_constellation.upper()} - {info['description']} 🌌")
                            print(f"{'=' * 60}")
                            print(f"\n📖 MYTHOLOGY:")
                            print(f"{info['mythology']}\n")
                            print(f"⭐ FEATURES:")
                            print(f"{info['features']}\n")
                            print(f"📅 BEST VIEWING SEASON:")
                            print(f"{info['best_season']}\n")
                            
                            # Show stars in this constellation
                            stars_in_const = get_stars_in_constellation(stars, selected_constellation)
                            if stars_in_const:
                                print(f"✨ STARS IN {selected_constellation.upper()}:")
                                print("-" * 60)
                                for star_name, star_data in stars_in_const:
                                    mag = star_data['magnitude']
                                    dist = star_data['distance']
                                    print(f"  • {star_name:<20} Mag: {mag:<6} Distance: {dist} ly")
                                print()
                    else:
                        print("Invalid selection.")
                except ValueError:
                    print("Invalid input.")
            
            elif browse_choice == "2":
                # Search by name
                search_name = input("\nEnter star name: ").strip().lower()
                if search_name in stars:
                    star_data = stars[search_name]
                    print(f"\n{'=' * 60}")
                    print(f"⭐ {search_name.upper()} ⭐")
                    print(f"{'=' * 60}")
                    print(f"Constellation: {star_data['constellation']}")
                    print(f"Magnitude: {star_data['magnitude']}")
                    print(f"Temperature: {star_data['temperature']} K")
                    print(f"Distance: {star_data['distance']} ly")
                    print(f"Radius: {star_data['radius']} times bigger than our sun")
                    
                    spectral_type = star_data['type'].upper()
                    if spectral_type in type_info:
                        print(f"\nSpectral Type: {spectral_type}")
                        print(f"Type info: {type_info[spectral_type]}")
                    print(f"{'=' * 60}\n")
                else:
                    print("Star not found in database.\n")
            else:
                print("Invalid choice.")
        
        elif learn_choice == "4":
            # Learn about all planets
            print(f"\n🪐 ALL PLANETS IN OUR SOLAR SYSTEM 🪐")
            print("=" * 70)
            
            planet_list = list(planets.keys())
            for i, name in enumerate(planet_list, 1):
                ptype = planets[name].get('type', 'Unknown')
                print(f"{i}. {name:<15} {ptype}")
            
            try:
                selection = int(input(f"\nSelect a planet to learn about (1-{len(planet_list)}): "))
                if 1 <= selection <= len(planet_list):
                    planet_name = planet_list[selection - 1]
                    planet_data = planets[planet_name]
                    
                    print(f"\n{'=' * 70}")
                    print(f"🪐 {planet_name.upper()} 🪐")
                    print(f"{'=' * 70}")
                    print(f"Type: {planet_data.get('type', 'Unknown')}")
                    print(f"Distance from Sun: {planet_data.get('distance_million_km', 'Unknown')} million km")
                    print(f"Diameter: {planet_data.get('diameter_km', 'Unknown')} km")
                    print(f"Mass: {planet_data.get('mass_earth_masses', 'Unknown')} Earth masses")
                    print(f"Orbital Period: {planet_data.get('orbital_period_days', 'Unknown')} days")
                    print(f"Day Length: {planet_data.get('rotation_period_hours', 'Unknown')} hours")
                    print(f"Known Moons: {planet_data.get('moons', 'Unknown')}")
                    
                    print(f"\n📖 MYTHOLOGY:")
                    print(f"{planet_data.get('mythology', 'No mythology available.')}")
                    print(f"\n⭐ FUN FACTS:")
                    print(f"{planet_data.get('fun_facts', 'No facts available.')}")
                    print(f"{'=' * 70}\n")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input.")
        
        elif learn_choice == "5":
            break
        
        else:
            print("Invalid choice. Please enter 1-5.")

def free_look_mode(stars, planets, observer_location, telescope):
    """Free Look Mode - continuous telescope exploration."""
    print("\n" + "=" * 70)
    print("🔭 FREE LOOK MODE")
    print("Enter 'exit' to return to menu.")
    print("=" * 70)
    
    moon_info = get_moon_info()
    
    while True:
        try:
            inp = input("\nEnter RA (0-360) or 'exit': ").strip()
            if inp.lower() == 'exit': break
            ra = float(inp)
            dec = float(input("Enter Dec (-90 to 90): "))
            
            # Slew telescope
            telescope.slew_to(ra, dec)
            
            # Identify what we are looking at
            current_planet_positions = calculate_planet_positions(observer_location[0], observer_location[1])
            current_moon_position = calculate_moon_position(observer_location[0], observer_location[1])
            
            obj_name, obj_info, obj_type, distance = find_object_by_coordinates(
                stars, planets, current_planet_positions, ra, dec, current_moon_position
            )
            
            if obj_name and obj_info:
                print(f"\n🎯 IDENTIFIED: {obj_name.upper()} ({obj_type})")
                print(f"   Distance from center: {distance:.2f}°")
                if input("   Learn more? (y/n): ").lower() == 'y':
                    if obj_type == 'star':
                         print(f"   Constellation: {obj_info.get('constellation')}")
                         print(f"   Magnitude: {obj_info.get('magnitude')}")
                    elif obj_type == 'planet':
                         print(f"   Type: {obj_info['data'].get('type')}")
                    elif obj_type == 'moon':
                         print(f"   Phase: {obj_info.get('phase')}")
            else:
                print(f"\n❌ Nothing identified at these coordinates.")
                
        except ValueError:
            print("Invalid input.")

def telescope_menu(stars, planets, planet_positions, observer_location, observer_name, telescope):
    """Full telescope control menu."""
    while True:
        print("\n" + "=" * 70)
        print("TELESCOPE CONTROLS")
        print("=" * 70)
        print("1. Look at the Moon 🌙")
        print("2. Look at Planets 🪐")
        print("3. Look at Star (Auto-Point Telescope) 🎯")
        print("4. Free Look Mode 🔭")
        print("5. Telescope View (Eyepiece) 👁️")
        print("6. Return to main menu")

        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            # Look at the Moon
            print("\n🌙 MOON VIEWER 🌙")
            print("=" * 70)
            
            moon_position = calculate_moon_position(observer_location[0], observer_location[1])
            moon_info = get_moon_info()
            
            if moon_position:
                # Show basic info first
                print(f"\n{moon_info['name']}")
                print(f"Current Phase: {moon_position['phase']} ({moon_position['illumination']}% illuminated)")
                print(f"Distance from Earth: {moon_position['distance_km']:,.0f} km")
                
                if moon_position['visible'] and moon_position['altitude'] > 0:
                    print(f"Status: ✓ VISIBLE (Altitude: {moon_position['altitude']:.1f}°)")
                    # NOTE: Passing the telescope object here fixes the crash
                    simulate_goto(telescope, "The Moon", moon_position['ra'], moon_position['dec'])
                    
                    if input("See info card? (y/n): ") == 'y': show_planet_image("Moon", {})
                else:
                    print(f"Status: ✗ Below horizon (Altitude: {moon_position['altitude']:.1f}°)")
            else:
                print("\nUnable to calculate Moon position.\n")

        elif choice == "2":
            # Look at Planets
            print("\n🪐 PLANET VIEWER 🪐")
            print("=" * 70)
            
            print("\nAvailable Planets:")
            planet_list = list(planet_positions.keys())
            for i, name in enumerate(planet_list, 1):
                print(f"{i}. {name}")
            
            try:
                selection = int(input(f"\nSelect planet number (1-{len(planet_list)}): "))
                if 1 <= selection <= len(planet_list):
                    planet_name = planet_list[selection - 1]
                    planet_pos = planet_positions[planet_name]
                    planet_data = planets.get(planet_name, {})
                    
                    # Show basic info first
                    print(f"\n{'=' * 70}")
                    print(f"🪐 {planet_name.upper()} 🪐")
                    print(f"{'=' * 70}")
                    print(f"Type: {planet_data.get('type', 'Unknown')}")
                    print(f"Distance from Earth: {planet_pos['distance_au']:.2f} AU")
                    
                    if planet_pos['visible'] and planet_pos['altitude'] > 0:
                        print(f"Status: ✓ VISIBLE (Altitude: {planet_pos['altitude']:.1f}°)")
                        # NOTE: Passing the telescope object here fixes the crash
                        simulate_goto(telescope, planet_name, planet_pos['ra'], planet_pos['dec'])
                        
                        if input("See info card? (y/n): ") == 'y': 
                            show_planet_image(planet_name, planet_data)
                    else:
                        print(f"Status: ✗ Below horizon (Altitude: {planet_pos['altitude']:.1f}°)")
            except ValueError:
                print("Invalid input.")

        elif choice == "3":
            # Look at Star feature (with telescope slewing)
            print("\n🔭 LOOK AT STAR SELECTOR 🔭")
            print("=" * 60)
            print("\nHow would you like to select your target?")
            print("1. Enter star name")
            print("2. Browse brightest stars")
            print("3. Select from a constellation")
            
            look_choice = input("\nEnter your choice: ").strip()
            
            target_star_name = None
            target_star_data = None
            
            if look_choice == "1":
                # Enter star name
                star_name = input("\nEnter the name of the star: ").strip().lower()
                
                # Don't allow Sun
                if star_name == "sun":
                    print("\n⚠️  Cannot auto-point to the Sun - it's too bright for telescope observation!")
                    print("Use solar filters and special equipment for solar observation.\n")
                    continue
                
                if star_name in stars:
                    target_star_name = star_name
                    target_star_data = stars[star_name]
                else:
                    print("Star not found in database.\n")
                    continue
            
            elif look_choice == "2":
                # Browse brightest stars
                bright_stars = list_bright_stars(stars, limit=30)
                
                print("\n✨ BRIGHTEST STARS ✨")
                print("=" * 60)
                for i, (name, data, mag) in enumerate(bright_stars, 1):
                    const = data.get('constellation', 'Unknown')
                    print(f"{i:2}. {name.title():<20} Mag: {mag:>6.1f}  ({const})")
                
                try:
                    selection = int(input("\nSelect star number: "))
                    if 1 <= selection <= len(bright_stars):
                        target_star_name, target_star_data, _ = bright_stars[selection - 1]
                    else:
                        print("Invalid selection.\n")
                        continue
                except ValueError:
                    print("Invalid input.\n")
                    continue
            
            elif look_choice == "3":
                # Select from constellation
                available_constellations = get_constellations_from_stars(stars)
                
                print("\n✨ Available Constellations ✨")
                for i, const in enumerate(available_constellations, 1):
                    print(f"{i}. {const}")
                
                try:
                    const_selection = int(input("\nSelect constellation number: "))
                    if 1 <= const_selection <= len(available_constellations):
                        selected_const = available_constellations[const_selection - 1]
                        
                        # Show stars in this constellation
                        stars_in_const = get_stars_in_constellation(stars, selected_const)
                        
                        print(f"\n✨ STARS IN {selected_const.upper()} ✨")
                        print("=" * 60)
                        for i, (name, data) in enumerate(stars_in_const, 1):
                            mag = data['magnitude']
                            print(f"{i:2}. {name:<20} Mag: {mag}")
                        
                        star_selection = int(input("\nSelect star number: "))
                        if 1 <= star_selection <= len(stars_in_const):
                            target_star_name, target_star_data = stars_in_const[star_selection - 1]
                            target_star_name = target_star_name.lower()
                        else:
                            print("Invalid selection.\n")
                            continue
                    else:
                        print("Invalid selection.\n")
                        continue
                except ValueError:
                    print("Invalid input.\n")
                    continue
            else:
                print("Invalid choice.\n")
                continue
            
            # Execute telescope movement if we have a target
            if target_star_name and target_star_data:
                # Check if star is visible (calculate altitude)
                ra = float(target_star_data['ra'])
                dec = float(target_star_data['dec'])
                
                # Calculate current altitude
                lst = calculate_lst(observer_location[1], datetime.utcnow())
                alt, az = ra_dec_to_alt_az(ra, dec, observer_location[0], observer_location[1], lst)
                
                if alt <= 0:
                    print(f"\n⚠️  {target_star_name.title()} is currently below the horizon!")
                    print(f"Current altitude: {alt:.1f}° (needs to be above 0°)")
                    print("Cannot point telescope at objects below the horizon.\n")
                    continue
                
                # Simulate the GoTo movement
                simulate_goto(telescope, target_star_name, ra, dec)
                
                # Basic identification
                print(f"\n{'=' * 70}")
                print(f"✨ NOW VIEWING: {target_star_name.upper()} ✨")
                print(f"{'=' * 70}")
                print(f"Distance: {target_star_data['distance']} ly")
                print(f"{'=' * 70}")
                
                # Learn more prompt
                learn_more = input("\nWould you like to learn more? (y/n): ").strip().lower()
                
                if learn_more == 'y':
                    print(f"\n{'=' * 70}")
                    print(f"✨ {target_star_name.upper()} - DETAILED INFORMATION ✨")
                    print(f"{'=' * 70}")
                    print(f"\nConstellation: {target_star_data['constellation']}")
                    print(f"Magnitude: {target_star_data['magnitude']}")
                    print(f"Temperature: {target_star_data['temperature']} K")
                    print(f"Distance: {target_star_data['distance']} ly")
                    print(f"Radius: {target_star_data['radius']} times bigger than our sun")
                    print(f"Coordinates: RA {target_star_data['ra']}°, Dec {target_star_data['dec']}°")
                    
                    spectral_type = target_star_data['type'].upper()
                    if spectral_type in type_info:
                        print(f"\nSpectral Type: {spectral_type}")
                        print(f"Type info: {type_info[spectral_type]}")
                    
                    # Show constellation info if available
                    const_name = target_star_data['constellation']
                    if const_name in constellation_info:
                        const_data = constellation_info[const_name]
                        print(f"\n🌌 CONSTELLATION: {const_name}")
                        print(f"{const_data['description']}")
                        print(f"\n📖 Mythology: {const_data['mythology'][:200]}...")
                    
                    print(f"{'=' * 70}")
                    
                    # See picture option
                    see_picture = input("\nWould you like to see a picture? (y/n): ").strip().lower()
                    if see_picture == 'y':
                        show_star_image(target_star_name, target_star_data)
                    
                    print(f"{'=' * 70}\n")
                else:
                    # See picture option even if not learning more
                    see_picture = input("\nWould you like to see a picture? (y/n): ").strip().lower()
                    if see_picture == 'y':
                        show_star_image(target_star_name, target_star_data)
                    print()

        elif choice == "4":
            free_look_mode(stars, planets, observer_location, telescope)

        elif choice == "5":
            moon_position = calculate_moon_position(observer_location[0], observer_location[1])
            telescope_view(stars, planets, planet_positions, observer_location, moon_position, telescope)

        elif choice == "6":
            break

def main():
    # 1. Initialize EVERYTHING ONCE
    telescope = SmartTelescope()
    stars = load_stars("stars.csv")
    planets = load_planets("planets.csv")
    
    # 2. Launch the HUD Window using THAT telescope and THAT star database
    hud = TelescopeHUD(telescope, stars)
    hud.start_hud_thread()

    # 3. Setup user details (Remove the duplicate 'telescope = ' lines here)
    observer_name = input("\nEnter your name: ")
    observer_location = (33.4484, -112.0740, "Phoenix, Arizona")
    telescope.set_location(observer_location[0], observer_location[1])

    # 4. Calculate initial planet positions
    planet_positions = calculate_planet_positions(observer_location[0], observer_location[1])
    
    # 5. Start the Menu Loop
        
    while True:
        print("\n" + "=" * 70)
        print("MAIN MENU")
        print("=" * 70)
        print("1. What's visible tonight? 🌃")
        print("2. Free Look Mode 🔭")
        print("3. Learn about celestial objects 📖")
        print("4. Full telescope controls 🔭")
        print("5. Exit")
        
        main_choice = input("\nWhat would you like to do? ").strip()
        
        if main_choice == "1":
            # Recalculate planet positions for current time
            planet_positions = calculate_planet_positions(observer_location[0], observer_location[1])
            moon_position = calculate_moon_position(observer_location[0], observer_location[1])
            
            # Show visibility information
            visible_planets, visible_stars, moon_pos = display_visibility_info(stars, planets, planet_positions, observer_location, moon_position)
            
            if visible_planets or visible_stars:
                while True:
                    print("\nWhat would you like to do?")
                    print("1. Look at a planet")
                    print("2. Look at a star")
                    print("3. Free Look Mode 🔭")
                    print("4. Return to main menu")
                    
                    vis_choice = input("\nEnter your choice: ").strip()
                    
                    if vis_choice == "1" and visible_planets:
                        # Look at planet
                        print("\nAvailable planets:")
                        for i, p in enumerate(visible_planets, 1):
                            print(f"{i}. {p['name']}")
                        
                        try:
                            planet_num = int(input(f"\nSelect planet (1-{len(visible_planets)}): "))
                            if 1 <= planet_num <= len(visible_planets):
                                selected = visible_planets[planet_num - 1]
                                planet_name = selected['name']
                                
                                # Check if planet is actually visible (above horizon)
                                if selected['altitude'] <= 0:
                                    print(f"\n⚠️  {planet_name} is currently below the horizon!")
                                    print(f"Current altitude: {selected['altitude']:.1f}° (needs to be above 0°)")
                                    print("Cannot point telescope at objects below the horizon.\n")
                                    continue
                                
                                simulate_goto(telescope, planet_name, selected['ra'], selected['dec'])
                                # ... Rest of the original visibility logic is preserved ...
                                
                                # Basic identification
                                planet_data = selected['data']
                                print(f"\n{'=' * 70}")
                                print(f"🪐 NOW VIEWING: {planet_name.upper()} 🪐")
                                print(f"{'=' * 70}")
                                print(f"Distance from Earth: {selected['distance_au']:.2f} AU")
                                print(f"Current altitude: {selected['altitude']:.1f}°")
                                print(f"{'=' * 70}")
                                
                                # Learn more prompt
                                learn_more = input("\nWould you like to learn more? (y/n): ").strip().lower()
                                
                                if learn_more == 'y':
                                    print("\n" + "=" * 70)
                                    print(f"🪐 {planet_name.upper()} - DETAILED INFORMATION 🪐")
                                    print("=" * 70)
                                    print(f"\nType: {planet_data.get('type', 'Unknown')}")
                                    print(f"Distance from Sun: {planet_data.get('distance_million_km', 'Unknown')} million km")
                                    print(f"Diameter: {planet_data.get('diameter_km', 'Unknown')} km")
                                    print(f"Mass: {planet_data.get('mass_earth_masses', 'Unknown')} Earth masses")
                                    print(f"Orbital Period: {planet_data.get('orbital_period_days', 'Unknown')} days")
                                    print(f"Day Length: {planet_data.get('rotation_period_hours', 'Unknown')} hours")
                                    print(f"Known Moons: {planet_data.get('moons', 'Unknown')}")
                                    
                                    print(f"\n📖 MYTHOLOGY:")
                                    print(f"{planet_data.get('mythology', 'No mythology available.')}")
                                    print(f"\n⭐ FUN FACTS:")
                                    print(f"{planet_data.get('fun_facts', 'No facts available.')}")
                                    print("=" * 70)
                                    
                                    # See picture option
                                    see_picture = input("\nWould you like to see a picture? (y/n): ").strip().lower()
                                    if see_picture == 'y':
                                        show_planet_image(planet_name, planet_data)
                                    
                                    print("=" * 70 + "\n")
                                else:
                                    # See picture option even if not learning more
                                    see_picture = input("\nWould you like to see a picture? (y/n): ").strip().lower()
                                    if see_picture == 'y':
                                        show_planet_image(planet_name, planet_data)
                                    print()
                            else:
                                print("Invalid selection.")
                        except ValueError:
                            print("Invalid input.")
                    
                    elif vis_choice == "2" and visible_stars:
                        # Look at star
                        try:
                            star_num = int(input(f"\nSelect star number (1-{len(visible_stars)}): "))
                            if 1 <= star_num <= len(visible_stars):
                                selected = visible_stars[star_num - 1]
                                star_name = selected['name']
                                star_data = selected['data']
                                
                                # Check if star is actually visible (above horizon)
                                if selected['altitude'] <= 0:
                                    print(f"\n⚠️  {star_name.title()} is currently below the horizon!")
                                    print(f"Current altitude: {selected['altitude']:.1f}° (needs to be above 0°)")
                                    print("Cannot point telescope at objects below the horizon.\n")
                                    continue
                                
                                ra = star_data['ra']
                                dec = star_data['dec']
                                
                                simulate_goto(telescope, star_name, ra, dec)
                                
                                # Basic identification
                                print(f"\n{'=' * 70}")
                                print(f"✨ NOW VIEWING: {star_name.upper()} ✨")
                                print(f"{'=' * 70}")
                                print(f"Distance: {star_data['distance']} ly")
                                print(f"Current altitude: {selected['altitude']:.1f}°")
                                print(f"{'=' * 70}")
                                
                                # Learn more prompt
                                learn_more = input("\nWould you like to learn more? (y/n): ").strip().lower()
                                
                                if learn_more == 'y':
                                    print("\n" + "=" * 70)
                                    print(f"✨ {star_name.upper()} - DETAILED INFORMATION ✨")
                                    print("=" * 70)
                                    print(f"\nConstellation: {star_data['constellation']}")
                                    print(f"Magnitude: {star_data['magnitude']}")
                                    print(f"Temperature: {star_data['temperature']} K")
                                    print(f"Distance: {star_data['distance']} ly")
                                    print(f"Radius: {star_data['radius']} times bigger than our sun")
                                    print(f"Coordinates: RA {star_data['ra']}°, Dec {star_data['dec']}°")
                                    
                                    spectral_type = star_data['type'].upper()
                                    if spectral_type in type_info:
                                        print(f"\nSpectral Type: {spectral_type}")
                                        print(f"Type info: {type_info[spectral_type]}")
                                    
                                    # Show constellation info if available
                                    const_name = star_data['constellation']
                                    if const_name in constellation_info:
                                        const_data = constellation_info[const_name]
                                        print(f"\n🌌 CONSTELLATION: {const_name}")
                                        print(f"{const_data['description']}")
                                        print(f"\n📖 Mythology: {const_data['mythology'][:200]}...")
                                    
                                    print("=" * 70)
                                    
                                    # See picture option
                                    see_picture = input("\nWould you like to see a picture? (y/n): ").strip().lower()
                                    if see_picture == 'y':
                                        show_star_image(star_name, star_data)
                                    
                                    print("=" * 70 + "\n")
                                else:
                                    # See picture option even if not learning more
                                    see_picture = input("\nWould you like to see a picture? (y/n): ").strip().lower()
                                    if see_picture == 'y':
                                        show_star_image(star_name, star_data)
                                    print()
                            else:
                                print("Invalid selection.")
                        except ValueError:
                            print("Invalid input.")
                    
                    elif vis_choice == "3":
                        # Free Look Mode
                        free_look_mode(stars, planets, observer_location, telescope)
                    
                    elif vis_choice == "4":
                        break
                    
                    else:
                        print("Invalid choice or no objects available for that option.")
        
        elif main_choice == "2":
            # Free Look Mode from main menu
            free_look_mode(stars, planets, observer_location, telescope)
        
        elif main_choice == "3":
            # Learn about celestial objects section
            learn_about_menu(stars, planets, planet_positions, observer_location)
        
        elif main_choice == "4":
            # Full telescope controls
            telescope_menu(stars, planets, planet_positions, observer_location, observer_name, telescope)
        
        elif main_choice == "5":
            print("\n🌌 Goodbye! Clear skies! 🌌\n")
            telescope.park()
            break
        
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")

if __name__ == "__main__":
    main()