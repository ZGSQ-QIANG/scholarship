import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
import base64

def process_pdf(file_input) -> str:
    """
    处理 PDF 文件，返回 Base64 编码的图片
    
    Args:
        file_input: 文件路径(str) 或 BytesIO 对象
    """
    if isinstance(file_input, str):
        doc = fitz.open(file_input)
    else:
        doc = fitz.open(stream=file_input.read(), filetype="pdf")
    
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=200)
    
    img_bytes = pix.tobytes("jpeg")
    doc.close()
    
    return base64.b64encode(img_bytes).decode("utf-8")

def process_image(file_input) -> str:
    """
    处理图片文件，返回 Base64 编码
    
    Args:
        file_input: 文件路径(str) 或 BytesIO 对象
    """
    img = Image.open(file_input)
    
    # 转换颜色模式
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    # 尺寸优化
    max_size = 1024
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))
    
    buffered = BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    
    img_bytes = buffered.getvalue()
    return base64.b64encode(img_bytes).decode("utf-8")