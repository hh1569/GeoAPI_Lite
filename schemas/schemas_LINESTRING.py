from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from starlette import status
from shapely.wkt import loads

from utils.mapping_table import CoordSys


class LinestringCreate(BaseModel):
    """创建线位入参"""
    name: str = Field(min_length=1, max_length=100, description="线位名称")
    address: str | None = Field(None, max_length=255, description="线位地址")
    geom: str = Field(
        pattern=r"^LINESTRING\(\d+\.?\d* \d+\.?\d*(?:, \d+\.?\d* \d+\.?\d*)+\)$",
        description="WKT格式线要素，例：LINESTRING(120 30, 121 31)",
        examples=["LINESTRING(120.0 30.0, 121.0 31.0)"]
    )
    coord_sys: int = Field(
        default=4326,
        description="坐标系SRID，默认4326(WGS84)。常用：4326(WGS84), 4490(CGCS2000), 3857(Web墨卡托)",
        examples=[4326, 4490, 3857]
    )

    @model_validator(mode="before")
    def check_geom_coords(cls, values):
        # 1. 取出 geom 和 coord_sys
        geom_wkt = values.get("geom")
        coord_sys = values.get("coord_sys", 4326)

        if not geom_wkt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="geom 不能为空"
            )

        try:
            # 2. 解析 WKT → 支持 点、线、面
            geom = loads(geom_wkt)

            # 3. 获取所有坐标点
            all_coords = list(geom.coords)#coords用来获取所有坐标点的工具

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="geom 格式不正确，请传入合法的 WKT 格式"
            )

        # 4. 只有 4326/4490 地理坐标系才校验经纬度范围
        if coord_sys in (4326, 4490):
            for lon, lat in all_coords:
                # 经度校验
                if not (-180 <= lon <= 180):
                    raise HTTPException(
                        status_code=400,
                        detail=f"geom 中存在不合法经度：{lon}，必须在 -180 ~ 180 之间"
                    )
                # 纬度校验
                if not (-90 <= lat <= 90):
                    raise HTTPException(
                        status_code=400,
                        detail=f"geom 中存在不合法纬度：{lat}，必须在 -90 ~ 90 之间"
                    )

        return values

class LinestringUpdate(BaseModel):
    """更新线入参"""
    name: str | None = Field(None, min_length=1, max_length=100, description="线位名称")
    address: str | None = Field(None, max_length=255, description="线位地址")
    geom: str | None = Field(
        None,
        pattern=r"^LINESTRING\(\d+\.?\d* \d+\.?\d*(?:, \d+\.?\d* \d+\.?\d*)+\)$",
        description="WKT格式线要素",
        examples=["LINESTRING(120.0 30.0, 121.0 31.0)"]
    )
    coord_sys: int | None = Field(
        default=None,
        description="坐标系SRID，默认不转换。常用：4326(WGS84), 4490(CGCS2000), 3857(Web墨卡托)",
        examples=[4326, 4490, 3857]
    )

    @model_validator(mode="before")
    def check_geom_coords(cls, values):
        # 1. 取出 geom 和 coord_sys
        geom_wkt = values.get("geom")
        coord_sys = values.get("coord_sys", 4326)
        if not geom_wkt:
            return values

        try:
            # 2. 解析 WKT → 支持 点、线、面
            geom = loads(geom_wkt)

            # 3. 获取所有坐标点
            all_coords = list(geom.coords)  # coords用来获取所有坐标点的工具

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="geom 格式不正确，请传入合法的 WKT 格式"
            )

        # 4. 只有 4326/4490 地理坐标系才校验经纬度范围
        if coord_sys in (4326, 4490):
            for lon, lat in all_coords:
                # 经度校验
                if not (-180 <= lon <= 180):
                    raise HTTPException(
                        status_code=400,
                        detail=f"geom 中存在不合法经度：{lon}，必须在 -180 ~ 180 之间"
                    )
                # 纬度校验
                if not (-90 <= lat <= 90):
                    raise HTTPException(
                        status_code=400,
                        detail=f"geom 中存在不合法纬度：{lat}，必须在 -90 ~ 90 之间"
                    )

        return values

class Geometry(BaseModel):
    type: str
    coordinates: Any  # 坐标：点是数组，面是二维数组

class Properties(BaseModel):
    id: int
    userid: int
    name: str
    address: str | None = None
    coord_sys: int = 4326
    create_time: str | None = None
    update_time: str | None = None

class LinestringDetail(BaseModel):
    """点位详情出参"""
    type : str
    geometry : Geometry
    properties: Properties

    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM对象属性取值
    )


