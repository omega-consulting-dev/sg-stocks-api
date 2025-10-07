from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from datetime import datetime

def generate_image():
    buffer = BytesIO()
    image = Image.new('RGB', (100, 100), 'red')
    image.save(buffer, format='JPEG')
    return SimpleUploadedFile(name="test.jpg", content=buffer.getvalue(), content_type="image/jpeg")

def format_date(date):

    if isinstance(date, str):
        try:
            date_obj = datetime.fromisoformat(date)
        except:
            return date
    elif isinstance(date, datetime):
        date_obj = date
    else:
        return None
    return date_obj.strftime("%d/%m/%Y %H:%M:%S")