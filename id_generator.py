import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import os
import random
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from ethiopian_date import EthiopianDateConverter
import re
from io import BytesIO
from rembg import remove
import io
import pytesseract
import logging

# === CONFIGURATION ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('id_generator.log'),
        logging.StreamHandler()
    ]
)

TEMPLATE_MAP = {
    "Template 1": "blank_1.jpg",
    "Template 2": "blank.jpg",
    "Template 3": "blank_1.jpg",
    "Template 4": "blank.jpg",
}

FONT_PATH = "fonts/PGUNICODE1.TTF"
FONT_SIZE = 24
GENERATED_FOLDER = "generated/"
os.makedirs(GENERATED_FOLDER, exist_ok=True)

def validate_pdf(pdf_bytes):
    """Validate PDF input before processing."""
    if not pdf_bytes:
        raise ValueError("Empty PDF bytes provided")
    if len(pdf_bytes) > 50 * 1024 * 1024:  # 50MB limit
        raise ValueError("PDF file too large")

def get_next_filename(folder_path, base_name):
    """Generate a unique filename with counter if needed."""
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)
    filename = f"{safe_name}.png"
    full_path = os.path.join(folder_path, filename)
    counter = 1
    while os.path.exists(full_path):
        filename = f"{safe_name}_{counter}.png"
        full_path = os.path.join(folder_path, filename)
        counter += 1
    return filename

def try_parse_date(date_str):
    """Robust date parsing with multiple format support."""
    date_str = str(date_str).strip()
    formats = [
        "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d",
        "%d-%m-%Y", "%b %d, %Y", "%d %b %Y",
        "%d/%m/%y", "%Y/%m/%d %H:%M:%S"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    clean_str = re.sub(r'[^0-9/:-]', '', date_str)
    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Could not parse date: {date_str}")

def find_ethiopian_date(date_obj):
    """Convert Gregorian date to Ethiopian date."""
    eth_date = EthiopianDateConverter.to_ethiopian(date_obj.year, date_obj.month, date_obj.day)
    eth_year, eth_month, eth_day = eth_date
    return f"{eth_year:04d}/{eth_month:02d}/{eth_day:02d}"

def pixmap_to_pil(pix):
    """Convert PyMuPDF pixmap to PIL Image."""
    if pix.colorspace.n != 3:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    return Image.open(BytesIO(pix.tobytes("ppm")))

def remove_background(pixmap):
    """Remove image background using rembg."""
    if pixmap.colorspace.n != 3:
        pixmap = fitz.Pixmap(fitz.csRGB, pixmap)

    img_bytes = io.BytesIO(pixmap.tobytes("png"))
    result = remove(img_bytes.getvalue())
    return Image.open(io.BytesIO(result))

def extract_text_from_pixmap(pixmap):
    """Extract text from image using OCR."""
    if pixmap.colorspace.n != 3:
        pixmap = fitz.Pixmap(fitz.csRGB, pixmap)
    img = Image.open(BytesIO(pixmap.tobytes("ppm")))
    text = pytesseract.image_to_string(img, config='--psm 6')
    return text.strip()

def extract_fin(pixmaps, pdf_name):
    """Extract FIN from document using multiple methods."""
    try:
        if len(pixmaps) >= 4:
            fin_img = Image.open(BytesIO(pixmaps[3].tobytes("ppm")))
            roi_boxes = [
                (1244, 2041, 1802, 2157),
                (1000, 2000, 2000, 2200)
            ]
            
            for box in roi_boxes:
                cropped_img = fin_img.crop(box)
                ocr_text = pytesseract.image_to_string(cropped_img, config='--psm 6')
                fin = re.sub(r'[^0-9A-Z]', '', ocr_text).strip()
                if len(fin) >= 6:
                    return fin
    except Exception as e:
        logging.warning(f"FIN extraction failed: {e}")
    
    return os.path.splitext(pdf_name)[0]

def parse_info_from_text(text):
    """Parse information from extracted text with robust error handling."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    info = {
        "FCN": "",
        "Full Name amh": "",
        "Full Name eng": "",
        "DOB ET": "",
        "DOB GR": "",
        "Gender amh": "",
        "Gender eng": "",
        "Nationality amh": "",
        "Nationality eng": "",
        "Phone Number": "",
        "Region amh": "",
        "Region eng": "",
        "Zone amh": "",
        "Zone eng": "",
        "Kebele amh": "",
        "Kebele eng": "",
    }
    
    try:
        if len(lines[0].strip()) > 20:
            info.update({
                "FCN": lines[56].strip().replace(" ", ""),
                "Full Name amh": lines[57].strip(),
                "Full Name eng": lines[58].strip(),
                "DOB ET": lines[43].strip(),
                "DOB GR": lines[44].strip(),
                "Gender amh": lines[45].strip(),
                "Gender eng": lines[46].strip(),
                "Nationality amh": lines[47].strip(),
                "Nationality eng": lines[48].strip(),
                "Phone Number": lines[49].strip(),
                "Region amh": lines[50].strip(),
                "Region eng": lines[51].strip(),
                "Zone amh": lines[52].strip(),
                "Zone eng": lines[53].strip(),
                "Kebele amh": lines[54].strip(),
                "Kebele eng": lines[55].strip(),
            })
        elif '|' in lines[1]:
            info.update({
                "FCN": lines[0],
                "Full Name amh": lines[1].split("|")[0].strip(),
                "Full Name eng": lines[1].split("|")[1].strip(),
                "DOB ET": lines[2].split("|")[0].strip(),
                "DOB GR": lines[2].split("|")[1].strip(),
                "Gender amh": lines[3].split("|")[0].strip(),
                "Gender eng": lines[3].split("|")[1].strip(),
                "Nationality amh": lines[4].split("|")[0].strip(),
                "Nationality eng": lines[4].split("|")[1].strip(),
                "Phone Number": lines[5].strip(),
                "Region amh": lines[6].split("|")[0].strip(),
                "Region eng": lines[6].split("|")[1].strip(),
                "Zone amh": lines[7].split("|")[0].strip(),
                "Zone eng": lines[7].split("|")[1].strip(),
                "Kebele amh": lines[8].split("|")[0].strip(),
                "Kebele eng": lines[8].split("|")[1].strip(),
            })
    except Exception as e:
        logging.error(f"Error parsing text: {e}")
        raise ValueError("Could not parse document text") from e
    
    return info

def draw_bold_text(draw, position, text, font, fill):
    """Draw bold text by offsetting."""
    x, y = position
    for offset in range(0, 2):
        draw.text((x + offset, y), text, font=font, fill=fill)
        draw.text((x, y + offset), text, font=font, fill=fill)

def draw_bold_large_text(draw, position, text, font_path, fill, size):
    """Draw bold large text with specified font size."""
    x, y = position
    font = ImageFont.truetype(font_path, size)
    for offset in range(0, 2):
        draw.text((x + offset, y), text, font=font, fill=fill)
        draw.text((x, y + offset), text, font=font, fill=fill)

def draw_rotated_bold_text(draw, position, text, font, fill, rotation_angle, base_image):
    """Draw rotated bold text."""
    temp_img = Image.new('RGBA', (500, 500), (255, 255, 255, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    for offset in range(0, 2):
        temp_draw.text((10 + offset, 10), text, font=font, fill=fill)
        temp_draw.text((10, 10 + offset), text, font=font, fill=fill)
    rotated_img = temp_img.rotate(rotation_angle, expand=1)
    base_image.paste(rotated_img, position, rotated_img)

def generate_id_card(pdf_bytes, pdf_name, template_name):
    """Main function to generate ID card from PDF."""
    try:
        # Validate input
        validate_pdf(pdf_bytes)
        
        # Open PDF document
        doc = fitz.open("pdf", pdf_bytes)
        if len(doc) == 0:
            raise ValueError("Empty PDF document")
        
        # Extract content
        text = doc[0].get_text()
        image_list = doc[0].get_images(full=True)
        pixmaps = [fitz.Pixmap(doc.extract_image(img[0])["image"]) for img in image_list]

        if len(pixmaps) < 2:
            raise ValueError("Not enough images in the PDF (expected at least 2).")

        # Process images
        try:
            photo_img = remove_background(pixmaps[0])
            if photo_img.mode != 'RGBA':
                photo_img = photo_img.convert('RGBA')
        except Exception as e:
            logging.warning(f"Background removal failed: {e}")
            photo_img = pixmap_to_pil(pixmaps[0])
            if photo_img.mode != 'RGBA':
                photo_img = photo_img.convert('RGBA')

        qr_img = pixmap_to_pil(pixmaps[1])

        # Extract and parse information
        info = parse_info_from_text(text)
        fin = extract_fin(pixmaps, pdf_name)
        
        # Calculate dates
        future_date = date.today() + relativedelta(years=8) - timedelta(days=2)
        
        # Format information
        info.update({
            "FIN": fin,
            "SN": random.randint(100000, 999999),
            "GDay GR": date.today(),
            "GDay ET": find_ethiopian_date(date.today()),
            "EDay GR": future_date,
            "EDay ET": find_ethiopian_date(future_date),
        })

        if info['Phone Number']:
            info['Phone Number'] = "+251 " + " ".join([info['Phone Number'][1:][i:i+3] for i in range(0, len(info['Phone Number'][1:]), 3)])
        
        if info['FCN']:
            info['FCN'] = " ".join([info['FCN'][i:i+4] for i in range(0, len(info['FCN']), 4)])
        
        try:
            info['DOB GR'] = try_parse_date(info['DOB GR']).strftime("%Y/%b/%d")
            info['DOB ET'] = try_parse_date(info['DOB ET']).strftime("%Y/%m/%d")
            info['EDay GR'] = info['EDay GR'].strftime("%Y/%b/%d")
        except Exception as e:
            logging.error(f"Date formatting error: {e}")
            raise

        # Load template
        template_path = TEMPLATE_MAP.get(template_name, TEMPLATE_MAP["Template 1"])
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file missing: {template_path}")

        template = Image.open(template_path).convert("RGBA")
        draw = ImageDraw.Draw(template)
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

        # Composite images
        template.paste(photo_img.resize((293, 383)), (74, 168), photo_img)
        template.paste(qr_img.resize((515, 522)), (1574, 46))

        # Draw text fields
        draw_bold_large_text(draw, (404, 172), info["Full Name amh"], FONT_PATH, "black", 28)
        draw_bold_large_text(draw, (404, 223), info["Full Name eng"], FONT_PATH, "black", 28)
        draw_bold_large_text(draw, (404, 314), info["DOB ET"], FONT_PATH, "black", 28)
        draw_bold_large_text(draw, (582, 314), info["DOB GR"], FONT_PATH, "black", 28)
        draw_bold_large_text(draw, (404, 380), info["Gender amh"], FONT_PATH, "black", 28)
        draw_bold_large_text(draw, (507, 380), info["Gender eng"], FONT_PATH, "black", 28)
        draw_bold_large_text(draw, (582, 445), info["EDay GR"], FONT_PATH, "black", 28)
        draw_bold_large_text(draw, (410, 445), info["EDay ET"], FONT_PATH, "black", 28)
        draw_bold_large_text(draw, (477, 507), info["FCN"], FONT_PATH, "black", 22)
        draw_rotated_bold_text(draw, (0, -228), info["GDay GR"].strftime("%Y/%b/%d"), font, "black", 90, template)
        draw_rotated_bold_text(draw, (0, 32), info["GDay ET"], font, "black", 90, template)

        draw_bold_text(draw, (1158, 87), info["Phone Number"], font, "black")
        draw_bold_text(draw, (1154, 172), info["Nationality amh"], font, "black")
        draw_bold_text(draw, (1281, 172), info["Nationality eng"], font, "black")
        draw_bold_text(draw, (1158, 235), info["Region amh"], font, "black")
        draw_bold_text(draw, (1158, 263), info["Region eng"], font, "black")
        draw_bold_text(draw, (1158, 296), info["Zone amh"], font, "black")
        draw_bold_text(draw, (1158, 363), info["Zone eng"], font, "black")
        draw_bold_text(draw, (1158, 430), info["Kebele amh"], font, "black")
        draw_bold_text(draw, (1158, 462), info["Kebele eng"], font, "black")
        draw_bold_large_text(draw, (1270, 528), info["FIN"], FONT_PATH, "black", 20)
        draw_bold_large_text(draw, (1957, 587), str(info["SN"]), FONT_PATH, "black", 20)

        # Save output
        output_buffer = BytesIO()
        file_name = get_next_filename(GENERATED_FOLDER, os.path.splitext(pdf_name)[0])
        template.save(output_buffer, format="PNG")
        output_buffer.seek(0)
        output_buffer.name = file_name

        return output_buffer

    except Exception as e:
        logging.error(f"Error generating ID card: {e}", exc_info=True)
        raise