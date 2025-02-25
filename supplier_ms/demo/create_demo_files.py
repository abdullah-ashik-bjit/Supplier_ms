import base64
from PIL import Image, ImageDraw
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

def create_sample_logo():
    # Create a simple colored logo
    img = Image.new('RGB', (200, 200), color='white')
    d = ImageDraw.Draw(img)
    d.text((40,80), "Company\nLogo", fill='blue')
    
    # Save as PNG
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def create_sample_stamp():
    # Create a circular stamp
    img = Image.new('RGBA', (200, 200), (255,255,255,0))
    d = ImageDraw.Draw(img)
    d.ellipse([10, 10, 190, 190], outline='blue')
    d.text((50,90), "COMPANY\nSTAMP", fill='blue')
    
    # Save as PNG
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def create_sample_pdf(filename, title):
    # Create PDF with some content
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, title)
    c.drawString(100, 700, "Sample Document")
    c.drawString(100, 650, "For Demo Purposes Only")
    c.save()
    return buffer.getvalue()

# Create and save all sample files
files_to_create = {
    'sample_logo.png': create_sample_logo(),
    'sample_stamp.png': create_sample_stamp(),
    'sample_trade_license.pdf': create_sample_pdf("Trade License", "TRADE LICENSE"),
    'sample_incorporation.pdf': create_sample_pdf("Certificate of Incorporation", "CERTIFICATE OF INCORPORATION"),
    'sample_good_standing.pdf': create_sample_pdf("Good Standing", "CERTIFICATE OF GOOD STANDING"),
    'sample_establishment.pdf': create_sample_pdf("Establishment Card", "ESTABLISHMENT CARD"),
    'sample_vat.pdf': create_sample_pdf("VAT Certificate", "VAT REGISTRATION CERTIFICATE"),
    'sample_memorandum.pdf': create_sample_pdf("Memorandum", "MEMORANDUM OF ASSOCIATION"),
    'sample_id.pdf': create_sample_pdf("ID Document", "IDENTIFICATION DOCUMENT"),
    'sample_bank_letter.pdf': create_sample_pdf("Bank Letter", "BANK REFERENCE LETTER"),
    'sample_financials.pdf': create_sample_pdf("Financials", "FINANCIAL STATEMENTS"),
    'sample_certifications.pdf': create_sample_pdf("Certifications", "OTHER CERTIFICATIONS")
}

# First ensure the directory exists
os.makedirs('../../supplier_ms/static/demo', exist_ok=True)

# Save all files
for filename, content in files_to_create.items():
    with open(f'../../supplier_ms/static/demo/{filename}', 'wb') as f:
        f.write(content)

print("Demo files created successfully in ../../supplier_ms/static/demo/")