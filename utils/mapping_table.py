from enum import Enum

from models import PointFeature,LinestringFeature,PolygonFeature

class LayerName(str, Enum):
    point = "point"          # 点表
    line = "line"            # 线表
    polygon = "polygon"      # 面表



LAYER_MODEL_MAP = {
    LayerName.point: PointFeature,
    LayerName.line: LinestringFeature,
    LayerName.polygon: PolygonFeature,
}