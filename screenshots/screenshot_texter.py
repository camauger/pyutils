from PIL import Image
import pytesseract

img = Image.open("code_screenshot.png")
text = pytesseract.image_to_string(img)
print(text)
