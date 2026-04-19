from fastapi import APIRouter, UploadFile, File, FastAPI
import pandas as pd
import io

app = FastAPI()

@app.post("/batch/import-excel")
async def import_excel(file: UploadFile = File(...)):
    #file是文件对象，不是文件内容
    # 1. 读取上传的 Excel,得到的是 二进制字节（bytes）
    contents = await file.read()
    #pandas 的读取 Excel 函数
    #io.BytesIO(contents)#把二进制数据 → 包装成 “内存里的文件”让 pandas 以为这是一个真实的文件
    df = pd.read_excel(io.BytesIO(contents))

    # 2. 打印看看数据（你可以注释掉）
    print(type(df))
    print(df.to_dict(orient="records"))

    # 3. 在这里写你的批量入库逻辑
    # ...

    return {
        "message": "上传成功",
        "总行数": len(df)
    }