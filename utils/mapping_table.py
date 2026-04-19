from enum import Enum

from models import PointFeature,LinestringFeature,PolygonFeature

# 你后端定义好：前端只能选这 3 个
class LayerName(str, Enum):
    point = "point"          # 点表
    line = "line"            # 线表
    polygon = "polygon"      # 面表



LAYER_MODEL_MAP = {
    LayerName.point: PointFeature,
    LayerName.line: LinestringFeature,
    LayerName.polygon: PolygonFeature,
}