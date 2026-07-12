#!/usr/bin/env python3
"""
Private UHQ Keyword Generator
=============================
Produces a custom (private), high-commercial-intent (UHQ) list of shopping /
product buying-intent keywords for SEO / PPC research.

These are ordinary long-tail e-commerce search phrases: "buy X online",
"cheap X", "X for sale", "where to buy X", etc. The list is generated
fresh from this script (not scraped from public keyword tools) so it is
"private", and every pattern is a proven buying-intent construction so the
terms are "UHQ" (high commercial intent, low generic-noise).

Output: 30,000 unique keywords written to keywords_uhq.txt (and a CSV
with category + intent columns).
"""

import csv
import random
from itertools import product

random.seed(42)

# ---------------------------------------------------------------------------
# 1. PRODUCT NOUNS  (the "X" in each keyword)
#    Curated across major e-commerce verticals. These are real product names
#    people actually search for when they intend to buy.
# ---------------------------------------------------------------------------

PRODUCTS = [
    # Electronics
    "smartphone", "laptop", "tablet", "smartwatch", "earbuds", "headphones",
    "bluetooth speaker", "tv", "4k tv", "oled tv", "monitor", "keyboard",
    "mechanical keyboard", "mouse", "webcam", "router", "mesh wifi",
    "power bank", "usb c charger", "wireless charger", "action camera",
    "dash cam", "projector", "home theater", "soundbar", "gaming console",
    "vr headset", "drone", "e reader", "fitbit", "gopro", "kindle",
    "nintendo switch", "playstation", "xbox", "graphics card", "ssd",
    "hard drive", "ram", "cpu", "motherboard", "gaming chair", "desk lamp",
    "smart plug", "smart bulb", "smart thermostat", "security camera",
    "doorbell camera", "robot vacuum", "air purifier", "portable ac",
    # Phones & accessories
    "phone case", "screen protector", "phone stand", "pop socket",
    "car phone mount", "wireless earbuds", "phone charger", "cable organizer",
    # Computers & office
    "laptop stand", "external monitor", "docking station", "printer",
    "ink cartridge", "webcam light", "microphone", "ring light", "desk mat",
    "office chair", "standing desk", "paper shredder", "label maker",
    "whiteboard", "file cabinet", "printer paper", "stapler", "calculator",
    # Home & kitchen
    "air fryer", "instant pot", "slow cooker", "coffee maker", "espresso machine",
    "blender", "juicer", "toaster", "microwave", "refrigerator", "dishwasher",
    "oven", "cookware set", "knife set", "cutting board", "mixing bowl",
    "food storage", "water bottle", "thermos", "lunch box", "rice cooker",
    "electric kettle", "waffle maker", "sandwich maker", "vacuum cleaner",
    "steam mop", "robot mop", "humidifier", "dehumidifier", "heater",
    "space heater", "fan", "air conditioner", "water filter", "water pitcher",
    "kitchen scale", "can opener", "wine opener", "coffee grinder",
    "tea kettle", "baking sheet", "muffin tin", "cake pan", "pie dish",
    "dinnerware set", "glassware", "mug set", "cutlery set", "placemat",
    "tablecloth", "napkins", "towels", "bed sheets", "duvet cover",
    "comforter", "pillow", "pillow case", "mattress", "mattress topper",
    "blanket", "throw blanket", "quilt", "curtains", "blinds", "rug",
    "area rug", "doormat", "shower curtain", "bath mat", "soap dispenser",
    "tissue box", "trash can", "laundry basket", "iron", "steam iron",
    "clothes dryer", "washing machine", "storage bin", "shelf organizer",
    "coat rack", "mirror", "wall art", "picture frame", "vase", "candle",
    "incense", "diffuser", "plant pot", "garden hose", "lawn mower",
    "leaf blower", "snow blower", "pressure washer", "tool set", "drill",
    "cordless drill", "screwdriver set", "hammer", "wrench set", "pliers",
    "tape measure", "utility knife", "workbench", "tool box", "ladder",
    "step stool", "flashlight", "headlamp", "multimeter", "saw", "circular saw",
    "jigsaw", "sander", "paint sprayer", "garden tools", "shovel", "rake",
    "wheelbarrow", "compost bin", "bird feeder", "outdoor furniture",
    "patio set", "hammock", "gazebo", "umbrella", "fire pit", "grill",
    "bbq grill", "smoker", "cooler", "camping stove", "tent", "sleeping bag",
    # Fashion - women
    "dress", "summer dress", "maxi dress", "cocktail dress", "wedding dress",
    "blouse", "t shirt", "tank top", "sweater", "cardigan", "hoodie",
    "jacket", "denim jacket", "leather jacket", "coat", "trench coat",
    "pants", "jeans", "leggings", "shorts", "skirt", "mini skirt",
    "swimsuit", "bikini", "one piece swimsuit", "lingerie", "bra", "panties",
    "shapewear", "scarf", "hat", "beanie", "gloves", "socks", "tights",
    "pajamas", "nightgown", "robe", "suit", "blazer", "vest", "poncho",
    "jumpsuit", "playsuit", "cardigan", "kimono", "wrap top", "crop top",
    # Fashion - men
    "men t shirt", "polo shirt", "dress shirt", "oxford shirt", "henley",
    "men sweater", "men hoodie", "men jacket", "denim jeans", "chinos",
    "men shorts", "men suit", "tuxedo", "blazer", "vest", "men coat",
    "winter coat", "parka", "trench", "men underwear", "boxers", "briefs",
    "men socks", "tie", "bow tie", "cufflinks", "belt", "men scarf",
    "men hat", "beanie", "cap", "gloves", "pajama set", "robe",
    # Shoes
    "sneakers", "running shoes", "walking shoes", "trainers", "boots",
    "combat boots", "chelsea boots", "heeled boots", "sandals", "flip flops",
    "loafers", "oxfords", "derby shoes", "dress shoes", "ballet flats",
    "heels", "wedges", "mules", "clogs", "slippers", "athletic shoes",
    "basketball shoes", "soccer cleats", "hiking shoes", "work boots",
    "rain boots", "ski boots", "skate shoes", "canvas shoes", "espadrilles",
    # Bags
    "backpack", "laptop backpack", "school backpack", "travel backpack",
    "handbag", "tote bag", "shoulder bag", "crossbody bag", "clutch",
    "wallet", "card holder", "coin purse", "duffel bag", "gym bag",
    "suitcase", "carry on", "luggage", "weekender bag", "messenger bag",
    "fanny pack", "makeup bag", "pouch",
    # Jewelry & watches
    "necklace", "pendant", "chain", "bracelet", "bangle", "earrings",
    "stud earrings", "hoop earrings", "ring", "engagement ring", "wedding band",
    "anklet", "brooch", "watch", "smartwatch", "analog watch", "chronograph",
    "diamond ring", "pearl necklace", "gold chain", "silver earrings",
    # Beauty & health
    "lipstick", "lip gloss", "foundation", "mascara", "eyeliner", "eyeshadow",
    "blush", "concealer", "primer", "highlighter", "perfume", "cologne",
    "body lotion", "face cream", "serum", "moisturizer", "sunscreen",
    "face mask", "cleanser", "toner", "shampoo", "conditioner", "hair mask",
    "hair dryer", "flat iron", "curling iron", "hair clipper", "razor",
    "shaving cream", "toothbrush", "electric toothbrush", "toothpaste",
    "floss", "mouthwash", "deodorant", "makeup brush", "makeup palette",
    "nail polish", "nail file", "cuticle oil", "false lashes", "makeup sponge",
    "compact mirror", "vanity mirror", "hair brush", "comb", "tweezers",
    "mirror compact", "hand cream", "foot cream", "face roller", "jade roller",
    "vitamin c serum", "retinol", "hyaluronic acid", "beard oil", "beard trimmer",
    "massage gun", "foam roller", "yoga mat", "resistance band", "dumbbell",
    "kettlebell", "treadmill", "exercise bike", "row machine", "pull up bar",
    "jump rope", "ab wheel", "weight bench", "power rack", "supplements",
    "protein powder", "multivitamin", "fish oil", "probiotics", "melatonin",
    # Sports & outdoors
    "tent", "sleeping bag", "camping chair", "hiking backpack", "trekking pole",
    "water bottle", "insulated bottle", "cooler", "fishing rod", "fishing reel",
    "tackle box", "bicycle", "mountain bike", "road bike", "helmet", "bike lock",
    "bike light", "kayak", "paddleboard", "wetsuit", "surfboard", "skateboard",
    "snowboard", "ski", "golf clubs", "tennis racket", "badminton set",
    "soccer ball", "basketball", "football", "baseball glove", "volleyball",
    "ping pong table", "dart board", "pool table", "bowling ball", "boxing gloves",
    "punching bag", "yoga block", "pilates ring", "trampoline", "swing set",
    # Toys & games
    "lego set", "building blocks", "action figure", "doll", "plush toy",
    "teddy bear", "remote control car", "drone", "board game", "card game",
    "puzzle", "jigsaw puzzle", "video game", "console game", "toy truck",
    "play kitchen", "kids bike", "scooter", "balance bike", "train set",
    "marble run", "science kit", "art set", "musical toy", "baby walker",
    "blocks", "stuffed animal", "fidget toy", "rubik cube", "chess set",
    # Baby & kids
    "diapers", "baby wipes", "baby formula", "baby bottle", "pacifier",
    "bib", "baby clothes", "onesie", "baby blanket", "crib", "baby monitor",
    "stroller", "car seat", "high chair", "baby carrier", "playpen",
    "baby gate", "night light", "kids shoes", "kids backpack", "lunch box",
    "school supplies", "crayons", "coloring book", "kids watch", "kids tablet",
    # Pet
    "dog food", "cat food", "dog treats", "cat litter", "dog bed", "cat bed",
    "dog collar", "dog leash", "cat tree", "pet carrier", "fish tank",
    "aquarium", "bird cage", "hamster cage", "pet bowl", "automatic feeder",
    "pet fountain", "grooming brush", "pet shampoo", "dog toy", "cat toy",
    "scratching post", "pet door", "flea collar", "pet camera", "poop bag",
    # Books & media
    "novel", "cookbook", "comic book", "manga", "textbook", "journal",
    "planner", "notebook", "sketchbook", "coloring book", "encyclopedia",
    "biography", "self help book", "childrens book", "audiobook", "vinyl record",
    "cd", "dvd", "blu ray", "poster", "calendar", "greeting card",
    # Automotive
    "car phone mount", "dash cam", "car charger", "tire inflator", "jump starter",
    "car vacuum", "floor mats", "seat cover", "steering wheel cover",
    "car wax", "car polish", "windshield wiper", "oil filter", "air filter",
    "spark plug", "battery charger", "gps navigator", "roof rack", "bike rack",
    "car cover", "sun shade", "tire gauge", "tool kit", "first aid kit",
    "emergency kit", "snow chain", "wheel cleaner", "car perfume",
    # Musical instruments
    "guitar", "acoustic guitar", "electric guitar", "bass guitar", "ukulele",
    "piano", "keyboard piano", "violin", "drums", "cajon", "harmonica",
    "flute", "saxophone", "trumpet", "microphone", "audio interface",
    "studio monitor", "mixer", "headphone amp", "guitar amp", "capo",
    "guitar strings", "drumsticks", "music stand", "metronome", "tuner",
    # Crafts & hobbies
    "sewing machine", "knitting needles", "yarn", "crochet hook", "fabric",
    "scrapbook kit", "painting set", "watercolor", "acrylic paint", "canvas",
    "easel", "calligraphy set", "candle making kit", "soap making kit",
    "resin kit", "jewelry making kit", "beading kit", "embroidery kit",
    "3d printer", "printer filament", "cricut machine", "heat press",
    "sublimation printer", "vinyl cutter", "stamp set", "sticker maker",
    # Grocery & specialty
    "coffee beans", "tea leaves", "olive oil", "honey", "chocolate",
    "protein bar", "nuts", "dried fruit", "spices", "seasoning", "sauce",
    "pasta", "rice", "flour", "sugar", "salt", "vinegar", "matcha",
    "kombucha", "energy drink", "sparkling water", "juice", "syrup",
    # Furniture
    "sofa", "couch", "loveseat", "sectional", "recliner", "accent chair",
    "dining table", "coffee table", "side table", "desk", "bookshelf",
    "wardrobe", "dresser", "nightstand", "bed frame", "bunk bed", "crib",
    "bar stool", "bench", "ottoman", "tv stand", "media console", "console table",
    # Misc / gifts
    "gift basket", "gift card", "flowers", "bouquet", "chocolate box",
    "wine bottle", "subscription box", "mystery box", "care package",
    "personalized gift", "engraved gift", "photo book", "custom mug",
    "custom t shirt", "custom phone case", "custom necklace", "custom art",
    # Tech gadgets
    "smart home hub", "smart lock", "video doorbell", "smart scale",
    "smart light", "smart speaker", "streaming device", "chromecast",
    "fire stick", "apple tv", "nvidia shield", "ebook reader", "portable charger",
    "solar charger", "bluetooth adapter", "wifi extender", "ethernet cable",
    "hdmi cable", "usb hub", "sd card", "micro sd", "memory card", "webcam",
    "ring light", "green screen", "podcast mic", "studio headphones",
]

# ---------------------------------------------------------------------------
# 2. BUYING-INTENT PATTERNS  (the "UHQ" part)
#    Every pattern below expresses commercial / transactional intent.
#    {x} is replaced by the product noun.
# ---------------------------------------------------------------------------

PATTERNS = [
    "buy {x} online",
    "{x} for sale",
    "cheap {x}",
    "best {x} to buy",
    "where to buy {x}",
    "{x} near me",
    "discount {x}",
    "{x} free shipping",
    "{x} wholesale",
    "affordable {x}",
    "{x} deals",
    "{x} shop",
    "{x} store",
    "online {x} store",
    "{x} price",
    "{x} cheap price",
    "best price {x}",
    "buy {x} cheap",
    "{x} on sale",
    "{x} with fast delivery",
    "{x} clearance",
    "{x} outlet",
    "order {x} online",
    "{x} best deal",
    "low price {x}",
    "{x} under $50",
    "{x} under $100",
    "{x} black friday",
    "{x} cyber monday",
    "new {x}",
    "{x} in stock",
    "premium {x}",
    "top rated {x}",
    "{x} with coupon",
    "{x} bundle",
    "{x} gift idea",
    "small {x}",
    "large {x}",
    "{x} for beginners",
]

# ---------------------------------------------------------------------------
# 3. GEO / LOCALITY modifiers (adds a 3rd dimension to push the count up
#    while keeping intent high: "buy x online in <country>")
# ---------------------------------------------------------------------------

LOCALES = [
    "usa", "uk", "canada", "australia", "germany", "france", "india",
    "uae", "singapore", "philippines", "mexico", "brazil", "spain",
    "italy", "netherlands", "japan", "south africa", "nigeria", "pakistan",
]

# ---------------------------------------------------------------------------
# 4. GENERATE
# ---------------------------------------------------------------------------

def build_keywords():
    kws = set()

    # Tier 1: product x pattern  (core UHQ buying intent)
    for prod, pat in product(PRODUCTS, PATTERNS):
        kw = pat.format(x=prod)
        kws.add(kw)

    # Tier 2: localize the strongest patterns to multiply volume w/ intent
    strong_patterns = [
        "buy {x} online {loc}",
        "{x} for sale {loc}",
        "cheap {x} {loc}",
        "{x} store {loc}",
        "where to buy {x} in {loc}",
        "{x} free shipping {loc}",
        "online {x} store {loc}",
        "{x} wholesale {loc}",
    ]
    for prod, pat, loc in product(PRODUCTS, strong_patterns, LOCALES):
        kw = pat.format(x=prod, loc=loc)
        kws.add(kw)

    return kws


def main():
    kws = build_keywords()
    # Deterministic shuffle so the "private" list order is reproducible but
    # not the naive product-by-product ordering.
    kws = list(kws)
    random.shuffle(kws)

    # Trim or report target
    TARGET = 30000
    if len(kws) >= TARGET:
        kws = kws[:TARGET]
    else:
        # Should not happen with current sizes, but pad by repeating combos
        # with extra locale/marker suffixes if somehow short.
        i = 0
        while len(kws) < TARGET:
            base = PRODUCTS[i % len(PRODUCTS)]
            kws.append(f"buy {base} online deal {i}")
            i += 1

    # Write plain text (one keyword per line)
    with open("keywords_uhq.txt", "w", encoding="utf-8") as f:
        for kw in kws:
            f.write(kw + "\n")

    # Write CSV with derived category + intent columns
    def categorize(kw):
        for p in PRODUCTS:
            if p in kw:
                return p
        return "general"

    with open("keywords_uhq.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "product", "intent"])
        for kw in kws:
            w.writerow([kw, categorize(kw), "commercial"])

    print(f"Generated {len(kws):,} unique UHQ keywords")
    print("  -> keywords_uhq.txt  (plain list)")
    print("  -> keywords_uhq.csv  (keyword, product, intent)")


if __name__ == "__main__":
    main()
