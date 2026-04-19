from geoalchemy2.shape import to_shape
from shapely.geometry import Point, LineString, Polygon, mapping

# 1. 创建 Shapely 点对象
line = LineString([(116.403874, 39.914885), (117.403874, 39.914885), (118.403874, 39.914885)])
print(line.coords)
print(list(line.coords))
for lon, lat in line.coords:
    print(lon, lat)
# # 转换为 GeoJSON 字典
# list_=[point,line,polygon]
# for i in list_:
#     geo_dict = mapping(i)
#     print(geo_dict)






