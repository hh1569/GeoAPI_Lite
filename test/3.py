from geoalchemy2 import shape
from shapely.geometry import Point,LineString,Polygon

# 长这样
point = Point(116.403874, 39.914885)  # 经度, 纬度

print(point.x)       # 经度
print(point.y)       # 纬度
print(point.wkt)
print(type(point))    # 'Point'
from shapely.geometry import LineString

# 一串坐标连起来就是线
line = LineString([
    (116.403, 39.914),
    (116.405, 39.916),
    (116.407, 39.918)
])
print(line.wkt)
print(line.length)       # 线长度
print(type(line))         # 'LineString'

from shapely.geometry import Polygon

# 一圈坐标围起来就是面
polygon = Polygon([
    (116.403, 39.914),
    (116.405, 39.914),
    (116.405, 39.916),
    (116.403, 39.916),
    (116.403, 39.914)
])

print(polygon.area)      # 面积
print(type(polygon))      # 'Polygon'