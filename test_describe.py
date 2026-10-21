"""Regression tests for describe.py, built from real listing phrases (EN/FR/NL). Run: python3 test_describe.py"""
import describe

YES = [  # (text, flag that must be set)
    ("Minimum lease term of 1 year.", "long_only"), ("One-year lease, renewable", "long_only"), ("MIN. 1 YEAR CONTRACT", "long_only"),
    ("Bail de minimum 1an", "long_only"), ("huurcontract van 1 jaar", "long_only"), ("Durée du bail: 12 mois", "long_only"), ("Bail 3-6-9", "long_only"),
    ("Minimum stay: 3 months", "short_term"), ("durée minimum de séjour 3 mois", "short_term"), ("6 or 12 month rental", "short_term"),
    ("Short-term and mid-term stays welcome", "short_term"), ("minimale huurtermijn: 3 maanden", "short_term"),
    ("Registration is not possible", "no_domicile"), ("Pas de possibilité de domiciliation", "no_domicile"), ("geen inschrijving mogelijk", "no_domicile"),
    ("Address registration possible", "domicile_ok"), ("inschrijving is mogelijk", "domicile_ok"), ("Domiciliation est possible", "domicile_ok"),
    ("One person only", "no_couple"), ("Max 1 person", "no_couple"), ("Pas de couples", "no_couple"), ("geen koppels", "no_couple"),
    ("Semi-equipped open kitchen (refrigerator, stovetop, sink)", "fridge"), ("Fully equipped open kitchen", "fridge"), ("Cuisine équipée", "fridge"),
    ("volledig ingerichte keuken", "fridge"), ("equipped with essential appliances", "fridge"),
    ("Space for a washing machine", "laundry_hookup"), ("emplacement machine à laver", "laundry_hookup"),
    ("Washing machine in the apartment", "laundry_machine"), ("Fully furnished apartment", "furnished"), ("Appartement meublé", "furnished"),
    ("Rooms for rent in a house", "shared"), ("3 shared bathrooms", "shared"), ("Chambres à louer", "shared"), ("kamers te huur", "shared"),
]
NO = [  # (text, flag that must NOT be set)
    ("It can be furnished at an extra cost", "furnished"), ("meuble lavabo en bois", "furnished"), ("Unfurnished apartment", "furnished"),
    ("Semi-furnished", "furnished"), ("Short-term lease of 1 year", "short_term"),
    ("Minimum lease 1 year, shorter periods possible", "long_only"), ("Lease of 1 year or shorter on request", "long_only"),
    ("No shared kitchen, own bathroom", "shared"), ("2 chambres à louer", "shared"), ("Washing machine connection", "laundry_machine"),
    ("Shared laundry room with washing machine", "laundry_machine"), ("Domiciliation impossible", "domicile_ok"),
]

bad = 0
for text, flag in YES:
    if not describe.facts(text)[0][flag]:
        bad += 1; print("MISSED   ", flag, "<-", text)
for text, flag in NO:
    if describe.facts(text)[0][flag]:
        bad += 1; print("FALSE HIT", flag, "<-", text)
print(f"{len(YES) + len(NO) - bad}/{len(YES) + len(NO)} passed")
raise SystemExit(1 if bad else 0)
