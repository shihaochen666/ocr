from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
from io import BytesIO
import uvicorn
from PIL import Image
import numpy as np
from core.analysis import Analysis

app = FastAPI()

# 提供静态文件服务，指向 `static` 文件夹
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/ocr/{ocr_type}")
async def ocr_analysis(ocr_type:str,file: UploadFile = File(...)):
    # 读取上传的文件内容
    contents = await file.read()

    # 使用 BytesIO 将文件内容转换为字节流对象
    img_byte_stream = BytesIO(contents)
    # 将字节流转换为图片格式（PIL）
    try:
        img = Image.open(img_byte_stream)
        img = np.array(img)  # 转换为 np.ndarray 类型
    except Exception as e:
        return {"error": f"Failed to process image: {str(e)}"}

    result = Analysis(ocr_type,img)
    return {"analysis_result": result.data_handle(ocr_type)}
    # 根据 OCR 类型进行分析
    # if ocr_type == "OrdinaryInvoice":
    #     # 使用转换后的图像数据进行 OCR 识别
    #     result = OrdinaryInvoiceAnalysis(img)
    #     return {"analysis_result": result.analysis()}
    # if ocr_type == "VatInvoice":
    #     # 使用转换后的图像数据进行 OCR 识别
    #     result = VatInvoiceAnalysis(img)
    #     return {"analysis_result": result.analysis()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
