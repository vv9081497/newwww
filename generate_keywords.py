#!/usr/bin/env python3
"""
Private UHQ Keyword Generator  v2  (SHORT form)
==============================================
v1 produced long 4-6 word phrases ("buy X online in canada") that are noisy.
v2 produces SHORT, compact 2-3 word high-commercial-intent keywords only:

    cheap phone      watch sale      buy laptop
    shoes wholesale  tv discount     dress outlet
    best monitor     new camera      mens watch

Method (keeps it "private" / fresh, not a scraped public list):
  - A large single-word product-noun vocabulary (head terms).
  - Short 1-word buying-intent modifiers, prefixed or suffixed.
  - Combinatorial generation, dedup, deterministic shuffle, trimmed to 30k.
No geo/long-tail fluff, so every keyword is short and conversion-oriented.
"""

import csv
import random
from itertools import product

random.seed(7)

# ---------------------------------------------------------------------------
# Single-word product NOUNS (the head term). Broad e-commerce coverage.
# ---------------------------------------------------------------------------

NOUNS = [
    # electronics
    "phone", "smartphone", "laptop", "tablet", "smartwatch", "earbuds",
    "headphones", "speaker", "tv", "monitor", "keyboard", "mouse", "webcam",
    "router", "charger", "powerbank", "projector", "console", "drone",
    "ereader", "camera", "microphone", "modem", "hub", "adapter", "cable",
    "battery", "inverter", "printer", "scanner", "projector", "amplifier",
    "subwoofer", "turntable", "receiver", "antenna", "battery", "charger",
    # computers
    "desktop", "notebook", "chromebook", "server", "nas", "ssd", "harddrive",
    "ram", "processor", "gpu", "motherboard", "cooler", "heatsink", "psu",
    "webcam", "mic", "headset", "stylus", "dock", "stand", "trackpad",
    # phones & gear
    "case", "cover", "screen", "protector", "stand", "mount", "holder",
    "earphone", "headset", "gadget", "accessory", "cable", "cord", "plug",
    # home & kitchen
    "fridge", "oven", "microwave", "blender", "mixer", "kettle", "toaster",
    "fryer", "cooker", "grinder", "juicer", "coffee", "espresso", "teapot",
    "pot", "pan", "wok", "utensil", "knife", "cutter", "board", "strainer",
    "bowl", "plate", "cup", "mug", "glass", "bottle", "flask", "jug",
    "vacuum", "mop", "purifier", "humidifier", "heater", "fan", "ac",
    "iron", "steamer", "washer", "dryer", "cleaner", "diffuser", "humidifier",
    "mattress", "pillow", "duvet", "blanket", "quilt", "sheet", "towel",
    "curtain", "rug", "carpet", "lamp", "bulb", "light", "mirror", "clock",
    "vase", "candle", "incense", "pot", "planter", "vase", "frame", "art",
    # furniture
    "sofa", "couch", "chair", "table", "desk", "bed", "wardrobe", "dresser",
    "shelf", "cabinet", "bench", "stool", "ottoman", "recliner", "crib",
    "bookshelf", "nightstand", "buffet", "hutch", "console",
    # fashion women
    "dress", "blouse", "shirt", "sweater", "hoodie", "jacket", "coat",
    "pants", "jeans", "leggings", "shorts", "skirt", "swimsuit", "bikini",
    "lingerie", "bra", "scarf", "hat", "beanie", "gloves", "socks", "pajamas",
    "robe", "suit", "blazer", "vest", "kimono", "top", "jumpsuit", "cardigan",
    "tunic", "gown", "saree", "lehenga", "abaya", "hijab", "kaftan",
    # fashion men
    "tshirt", "polo", "trouser", "chino", "sneaker", "boot", "loafer",
    "derby", "oxford", "tuxedo", "waistcoat", "tie", "cufflink", "belt",
    "cap", "beanie", "underline", "boxer", "brief", "sock", "scarf",
    # shoes
    "sneakers", "trainers", "boots", "sandals", "flats", "heels", "wedges",
    "mules", "clogs", "slippers", "cleats", "runners", "hikers", "loafers",
    # bags
    "backpack", "handbag", "tote", "clutch", "wallet", "purse", "duffel",
    "suitcase", "luggage", "briefcase", "messenger", "pouch", "sling",
    "fanny", "weekender", "holdall",
    # jewelry & watches
    "necklace", "pendant", "chain", "bracelet", "bangle", "earring", "ring",
    "anklet", "brooch", "watch", "chronograph", "cuff", "tiara", "locket",
    # beauty
    "lipstick", "gloss", "foundation", "mascara", "eyeliner", "eyeshadow",
    "blush", "concealer", "primer", "perfume", "cologne", "lotion", "cream",
    "serum", "moisturizer", "sunscreen", "mask", "cleanser", "toner",
    "shampoo", "conditioner", "dryer", "iron", "trimmer", "razor", "brush",
    "comb", "mirror", "palette", "polish", "spray", "powder",
    # health & fitness
    "vitamin", "supplement", "protein", "multivitamin", "probiotic", "melatonin",
    "fishoil", "collagen", "whey", "creatine", "massager", "roller", "yogamat",
    "band", "dumbbell", "kettlebell", "treadmill", "bike", "rower", "bench",
    "rack", "jump", "abwheel", "scale", "thermometer", "blood", "meter",
    # sports & outdoor
    "tent", "hammock", "sleepingbag", "backpack", "trekking", "bottle",
    "cooler", "rod", "reel", "bicycle", "helmet", "lock", "light", "kayak",
    "paddle", "wetsuit", "surfboard", "skateboard", "snowboard", "ski",
    "club", "racket", "ball", "glove", "puck", "skate", "trampoline",
    "swing", "goal", "net", "mat",
    # toys & games
    "lego", "blocks", "figure", "doll", "plush", "bear", "car", "drone",
    "boardgame", "cardgame", "puzzle", "console", "toy", "truck", "kit",
    "cube", "chess", "rubic", "robot", "train",
    # baby & kids
    "diaper", "wipe", "formula", "bottle", "pacifier", "bib", "onesie",
    "blanket", "crib", "monitor", "stroller", "seat", "chair", "carrier",
    "gate", "shoe", "backpack", "crayon", "book",
    # pet
    "dogfood", "catfood", "treat", "litter", "bed", "collar", "leash",
    "tree", "carrier", "tank", "cage", "bowl", "fountain", "toy", "shampoo",
    # books & media
    "novel", "cookbook", "comic", "manga", "textbook", "journal", "planner",
    "notebook", "sketchbook", "audiobook", "vinyl", "cd", "dvd", "bluray",
    "poster", "calendar", "card",
    # automotive
    "mount", "charger", "inflator", "starter", "vacuum", "mat", "cover",
    "wax", "polish", "wiper", "filter", "battery", "tire", "gps", "rack",
    "seat", "cleaner", "perfume", "chain", "gauge",
    # music
    "guitar", "ukulele", "piano", "violin", "drums", "cajon", "harmonica",
    "flute", "saxophone", "trumpet", "mic", "interface", "mixer", "monitor",
    "amp", "capo", "string", "stick", "stand", "tuner", "metronome",
    # crafts
    "machine", "needle", "yarn", "hook", "fabric", "kit", "paint", "canvas",
    "easel", "stamp", "sticker", "resin", "bead", "thread", "scissors",
    "cutter", "printer", "filament", "vinyl", "press",
    # grocery
    "coffee", "tea", "oil", "honey", "chocolate", "bar", "nuts", "spice",
    "sauce", "pasta", "rice", "flour", "sugar", "salt", "vinegar", "matcha",
    "juice", "syrup", "cocoa", "cereals",
    # gifts & misc
    "basket", "flowers", "bouquet", "wine", "box", "package", "mug", "art",
    "poster", "card", "hamper",
]

# ---------------------------------------------------------------------------
# SHORT buying-intent MODIFIERS (1 word each) -> keeps keywords 2-3 words.
# ---------------------------------------------------------------------------

PREFIX = [
    "buy", "cheap", "best", "new", "used", "premium", "top", "affordable",
    "discount", "wholesale", "luxury", "mens", "womens", "kids", "girls",
    "boys", "small", "large", "wireless", "smart", "organic", "vegan",
    "custom", "bulk", "hot", "trending",
]

SUFFIX = [
    "shop", "store", "sale", "price", "deal", "online", "cheap", "discount",
    "wholesale", "outlet", "clearance", "near", "uk", "usa", "india",
    "canada", "au", "de", "ae", "ph",
]

# ---------------------------------------------------------------------------
# GENERATE
# ---------------------------------------------------------------------------

def build():
    kws = set()
    for n in NOUNS:
        for m in PREFIX:
            kws.add(f"{m} {n}")
        for m in SUFFIX:
            kws.add(f"{n} {m}")
    return kws


def main():
    kws = build()
    kws = list(kws)
    random.shuffle(kws)

    TARGET = 30000
    if len(kws) < TARGET:
        i = 0
        while len(kws) < TARGET:
            kws.append(f"cheap {NOUNS[i % len(NOUNS)]} {i}")
            i += 1
    else:
        kws = kws[:TARGET]

    with open("keywords_uhq.txt", "w", encoding="utf-8") as f:
        for kw in kws:
            f.write(kw + "\n")

    with open("keywords_uhq.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["keyword", "product", "intent"])
        for kw in kws:
            prod = kw.split(" ", 1)[-1] if kw.split(" ", 1)[-1] in NOUNS else kw.split(" ")[-1]
            w.writerow([kw, prod, "commercial"])

    print(f"Generated {len(kws):,} short UHQ keywords")


if __name__ == "__main__":
    main()
