
data_list = [{"coordinates":"116.300 39.900, 116.310 39.900, 116.310 39.910, 116.300 39.910, 116.300 39.900"}]
for item in data_list:
    # 从 Excel 获取坐标字符串，
    coords_str = item["coordinates"]
    print(coords_str)

    # 把坐标转换成 LINESTRING 格式
    # 1. 按 , 分割成多个点
    coord_list = coords_str.split(",")
    print(coord_list)

    # 2. replace()把每个点的 , 换成空格（WKT 标准格式）
    # ", ".join()用 "," 把所有处理好的坐标连起来
    list_ = [coord.replace(",", " ") for coord in coord_list]
    print(list_)

    wkt_coords = ", ".join(list_)#把列表里面的字符取出来，然后用，连接。
    print(wkt_coords)