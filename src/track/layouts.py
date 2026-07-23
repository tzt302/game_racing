"""Hand-modelled centreline anchors for real-world Grand Prix circuits.

The anchors are original, simplified gameplay geometry traced with reference to
public track diagrams.  They are smoothed and rescaled to the real lap length by
``Track``; no third-party image is shipped with the game.
"""

TRACK_ORDER = ["spa", "silverstone", "monza", "monaco", "shanghai"]

TRACKS = {
    "spa": {
        "name": "SPA-FRANCORCHAMPS",
        "country": "BELGIUM",
        "length_m": 7004,
        "width": 15.0,
        "laps": 3,
        "accent": (255, 196, 35),
        "description": "High speed • elevation-inspired flow • 19 corners",
        "anchors": [
            (8, 76), (14, 61), (11, 48), (20, 35), (34, 25), (48, 18),
            (62, 12), (75, 15), (82, 24), (76, 33), (64, 39), (69, 48),
            (83, 55), (91, 66), (87, 78), (76, 87), (62, 90), (49, 86),
            (41, 76), (33, 65), (25, 70), (20, 82), (12, 88), (6, 84),
        ],
    },
    "silverstone": {
        "name": "SILVERSTONE",
        "country": "GREAT BRITAIN",
        "length_m": 5891,
        "width": 15.0,
        "laps": 3,
        "accent": (65, 210, 245),
        "description": "Fast direction changes • flowing complexes • 18 corners",
        "anchors": [
            (18, 72), (10, 60), (12, 43), (25, 37), (38, 42), (47, 34),
            (58, 22), (75, 17), (88, 23), (84, 34), (70, 38), (60, 44),
            (69, 53), (84, 57), (91, 68), (85, 82), (69, 88), (54, 82),
            (48, 69), (38, 61), (28, 65), (29, 77), (24, 86), (15, 84),
        ],
    },
    "monza": {
        "name": "MONZA",
        "country": "ITALY",
        "length_m": 5793,
        "width": 15.0,
        "laps": 3,
        "accent": (245, 65, 65),
        "description": "Low downforce • long straights • heavy braking",
        "anchors": [
            (23, 86), (14, 75), (13, 48), (17, 19), (28, 11), (38, 15),
            (39, 28), (31, 35), (40, 42), (55, 36), (73, 25), (87, 30),
            (91, 45), (84, 60), (70, 69), (61, 79), (49, 87), (35, 91),
        ],
    },
    "monaco": {
        "name": "MONACO",
        "country": "MONACO",
        "length_m": 3337,
        "width": 11.0,
        "laps": 4,
        "accent": (245, 73, 83),
        "description": "Street circuit • narrow barriers • 19 corners",
        "anchors": [
            (18, 72), (9, 62), (13, 48), (26, 42), (33, 30), (27, 18),
            (39, 10), (55, 15), (63, 27), (73, 34), (88, 37), (91, 50),
            (83, 58), (69, 54), (59, 61), (72, 69), (82, 78), (73, 89),
            (58, 87), (49, 76), (40, 70), (31, 79), (22, 87), (13, 83),
        ],
    },
    "shanghai": {
        "name": "SHANGHAI",
        "country": "CHINA",
        "length_m": 5451,
        "width": 15.0,
        "laps": 3,
        "accent": (232, 45, 55),
        "description": "Technical opening spiral • long back straight • 16 corners",
        "anchors": [
            (18, 76), (10, 65), (11, 49), (20, 40), (31, 42), (37, 51),
            (31, 59), (22, 57), (19, 48), (29, 33), (44, 25), (58, 17),
            (73, 14), (87, 21), (90, 34), (82, 43), (68, 48), (62, 58),
            (71, 67), (86, 69), (91, 80), (83, 90), (67, 89), (51, 82),
            (39, 72), (28, 68),
        ],
    },
}

