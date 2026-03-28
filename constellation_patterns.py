"""
Constellation Pattern Database
Defines how to connect stars to form constellation shapes
"""

# Format: constellation_name: [(star1, star2), (star2, star3), ...]
# These are the actual lines that form recognizable constellation patterns

CONSTELLATION_LINES = {
    "Orion": [
        # The body and belt
        ("betelgeuse", "bellatrix"),
        ("bellatrix", "alnitak"),
        ("alnitak", "alnilam"),
        ("alnilam", "mintaka"),
        ("mintaka", "rigel"),
        ("rigel", "saiph"),
        ("saiph", "betelgeuse"),
        # The sword
        ("alnilam", "hatysa"),
    ],
    
    "Ursa Major": [
        # Big Dipper bowl
        ("dubhe", "merak"),
        ("merak", "phecda"),
        ("phecda", "megrez"),
        ("megrez", "dubhe"),
        # Big Dipper handle
        ("megrez", "alioth"),
        ("alioth", "mizar"),
        ("mizar", "alkaid"),
    ],
    
    "Canis Major": [
        ("sirius", "mirzam"),
        ("sirius", "wezen"),
        ("wezen", "adhara"),
        ("adhara", "aludra"),
    ],
    
    "Lyra": [
        ("vega", "sheliak"),
        ("vega", "sulafat"),
    ],
    
    "Gemini": [
        # The twins
        ("castor", "pollux"),
        ("castor", "alhena"),
        ("pollux", "alhena"),
    ],
    
    "Leo": [
        # The Sickle (head)
        ("regulus", "algieba"),
        ("algieba", "adhafera"),
        # The body
        ("regulus", "denebola"),
        ("denebola", "zosma"),
    ],
    
    "Scorpius": [
        # The head
        ("antares", "dschubba"),
        # The tail
        ("antares", "shaula"),
    ],
    
    "Cygnus": [
        # The Northern Cross
        ("deneb", "sadr"),
        ("sadr", "albireo"),
        ("sadr", "gienah"),
    ],
    
    "Cassiopeia": [
        # The W shape
        ("schedar", "caph"),
        ("caph", "cih"),
        ("cih", "ruchbah"),
    ],
    
    "Taurus": [
        # The V face
        ("aldebaran", "ain"),
        # Bull's horns
        ("aldebaran", "alnath"),
    ],
    
    "Aquila": [
        ("altair", "alshain"),
        ("altair", "tarazed"),
    ],
    
    "Centaurus": [
        ("rigel kentaurus", "hadar"),
    ],
    
    "Crux": [
        # The Southern Cross
        ("acrux", "mimosa"),
        ("gacrux", "imai"),
    ],
}

# Simple constellation figure descriptions (for artistic overlay)
CONSTELLATION_FIGURES = {
    "Orion": {
        "type": "hunter",
        "description": "A hunter with raised club and shield",
        "key_stars": ["betelgeuse", "rigel", "bellatrix", "saiph"]
    },
    "Ursa Major": {
        "type": "bear", 
        "description": "A great bear",
        "key_stars": ["dubhe", "merak", "alkaid"]
    },
    "Canis Major": {
        "type": "dog",
        "description": "A hunting dog",
        "key_stars": ["sirius"]
    },
    "Leo": {
        "type": "lion",
        "description": "A lion with distinctive mane",
        "key_stars": ["regulus", "denebola"]
    },
}
