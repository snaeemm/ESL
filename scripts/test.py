from PIL import Image, ImageDraw, ImageFont

# 1. Canvas Setup
width, height = 800, 450
bg_color = (244, 241, 234)  # Light off-white background
img = Image.new("RGB", (width, height), bg_color)
draw = ImageDraw.Draw(img)

# Color Palette
OUTLINE = (90, 90, 90)
SOFT_OUTLINE = (170, 170, 170)
AGAL_BLACK = (35, 35, 35)
AGAL_HILITE = (75, 75, 75)
SKIN = (198, 128, 80)
SKIN_SHADOW = (170, 105, 62)
DARK_BROWN = (75, 42, 20)
WHITE_FABRIC = (255, 255, 255)
FABRIC_SHADOW = (222, 222, 222)

cx = width // 2  # 400

# 2. Shoulders / Thobe body (drawn first, behind everything)
draw.polygon(
    [(150, 450), (230, 300), (280, 275), (500, 275), (570, 300), (650, 450)],
    fill=WHITE_FABRIC, outline=OUTLINE, width=3,
)

# 3. Arms bent up toward chest, ending in hands near the middle
# Left arm (image-left)
draw.polygon(
    [(230, 300), (150, 450), (270, 450), (310, 370), (330, 320), (300, 305)],
    fill=WHITE_FABRIC, outline=OUTLINE, width=3,
)
# Right arm (image-right)
draw.polygon(
    [(570, 300), (650, 450), (530, 450), (490, 370), (470, 320), (500, 305)],
    fill=WHITE_FABRIC, outline=OUTLINE, width=3,
)
# Soft crease lines on sleeves
draw.line([(265, 340), (305, 375)], fill=SOFT_OUTLINE, width=2)
draw.line([(535, 340), (495, 375)], fill=SOFT_OUTLINE, width=2)

# 4. Hands making the "search / find" crossed-finger gesture, near chest
def draw_hand(cx_h, cy_h, mirror=1):
    # palm
    draw.ellipse([cx_h - 26, cy_h - 20, cx_h + 26, cy_h + 24], fill=SKIN, outline=OUTLINE, width=2)
    # two crossed fingers (index over middle), pointing up-and-in toward center
    dx = -1 if mirror == 1 else 1
    f1 = [(cx_h + dx * 6, cy_h - 5), (cx_h + dx * 34, cy_h - 55), (cx_h + dx * 42, cy_h - 52), (cx_h + dx * 16, cy_h)]
    f2 = [(cx_h - dx * 6, cy_h - 5), (cx_h - dx * 22, cy_h - 58), (cx_h - dx * 12, cy_h - 62), (cx_h + dx * 6, cy_h - 8)]
    draw.polygon(f1, fill=SKIN, outline=OUTLINE, width=2)
    draw.polygon(f2, fill=SKIN, outline=OUTLINE, width=2)
    # thumb tucked to the side
    thumb_x0 = cx_h - 24 if mirror == 1 else cx_h + 6
    thumb_x1 = thumb_x0 + 18
    draw.ellipse([thumb_x0, cy_h + 4, thumb_x1, cy_h + 26], fill=SKIN, outline=OUTLINE, width=2)

draw_hand(325, 345, mirror=1)
draw_hand(475, 345, mirror=-1)

# 5. Ghutra (headscarf) draping from crown down over the shoulders
draw.polygon(
    [(cx, 60), (300, 130), (230, 300), (300, 300), (cx, 240), (500, 300), (570, 300), (500, 130)],
    fill=WHITE_FABRIC, outline=OUTLINE, width=3,
)
# subtle fold shading down the drape
draw.line([(340, 150), (300, 290)], fill=FABRIC_SHADOW, width=4)
draw.line([(460, 150), (500, 290)], fill=FABRIC_SHADOW, width=4)
draw.line([(cx, 90), (cx, 235)], fill=FABRIC_SHADOW, width=3)

# 6. Face (drawn on top of the ghutra drape)
draw.ellipse([335, 95, 465, 245], fill=SKIN, outline=OUTLINE, width=3)
# soft cheek shading
draw.ellipse([335, 150, 380, 210], fill=SKIN_SHADOW, outline=None)
draw.ellipse([420, 150, 465, 210], fill=SKIN_SHADOW, outline=None)
draw.ellipse([335, 95, 465, 245], fill=None, outline=OUTLINE, width=3)

# Face features
draw.arc([358, 128, 396, 145], start=180, end=360, fill=DARK_BROWN, width=4)  # left eyebrow
draw.arc([404, 128, 442, 145], start=180, end=360, fill=DARK_BROWN, width=4)  # right eyebrow
draw.ellipse([368, 148, 384, 164], fill=DARK_BROWN)  # left eye
draw.ellipse([416, 148, 432, 164], fill=DARK_BROWN)  # right eye
draw.line([(400, 168), (400, 190)], fill=DARK_BROWN, width=3)  # nose
draw.line([(383, 210), (417, 210)], fill=DARK_BROWN, width=4)  # mouth

# 7. Agal (black cords) resting on the crown of the head
draw.rounded_rectangle([328, 92, 472, 122], radius=15, fill=AGAL_BLACK, outline=OUTLINE, width=2)
draw.rounded_rectangle([328, 100, 472, 112], radius=8, fill=AGAL_HILITE)

# 8. Thobe placket line and tassel (visible below the crossed hands)
draw.line([(cx, 245), (cx, 320)], fill=WHITE_FABRIC, width=8)
draw.line([(cx - 3, 245), (cx - 3, 320)], fill=SOFT_OUTLINE, width=1)
draw.line([(cx + 3, 245), (cx + 3, 320)], fill=SOFT_OUTLINE, width=1)

# 9. Bottom Banner (Translucent Dark Bar)
banner = Image.new("RGBA", (width, 70), (40, 40, 40, 210))
img.paste(banner, (0, height - 70), banner)

# 10. Add Labels ("Find" and Arabic Text "يكتشف")
draw_text = ImageDraw.Draw(img)
draw_text.text((20, height - 55), "Find", fill=(255, 255, 255))
draw_text.text((width - 110, height - 55), "يكتشف", fill=(255, 255, 255))

# Save Image
img.save("emirati_garb_illustration.png")
