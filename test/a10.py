from enum import Enum

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="空间查询测试")

# 下拉选择枚举
class LayerType(str, Enum):
    point = "point1111"
    line = "line111111"
    polygon = "polygon1111"


# 下拉选择接口
@app.get("/select-layer")
async def select_layer(layer: LayerType):
    return {"你选择的图层": layer}

# 固定正确启动

if __name__ == '__main__':
    # 直接用 "a10:app" 即可！
    uvicorn.run("a10:app", host="127.0.0.1", port=8888, reload=True)