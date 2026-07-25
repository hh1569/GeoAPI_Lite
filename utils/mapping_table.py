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

# 常用坐标系枚举
class CoordSys(int, Enum):
    WGS84 = 4326           # WGS84 GPS坐标（国际通用）
    CGCS2000 = 4490        # 国家大地坐标系
    WEB_MERCATOR = 3857    # Web墨卡托投影

# 坐标系验证正则（允许用户输入自定义 SRID）
def validate_srid(srid: int) -> bool:
    """验证 SRID 是否合法（1-999999）"""
    return 1 <= srid <= 999999