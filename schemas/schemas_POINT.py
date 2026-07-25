from typing import Any

import shapely
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from datetime import datetime
from shapely.wkt import loads
from starlette import status

from utils.mapping_table import CoordSys


# ------------------------------
# 入参模型
# ------------------------------
class PointCreate(BaseModel):
    """创建点位入参"""
    name: str = Field(min_length=1, max_length=100, description="点位名称")
    address: str | None = Field(None, max_length=255, description="点位地址")
    geom: str = Field(
        pattern=r"^POINT\(\d+\.?\d* \d+\.?\d*\)$",
        description="WKT格式点位，例：POINT(120.0 30.0)",
        examples=["POINT(120.0 30.0)"]
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
            geom = loads(geom_wkt)

            lon = geom.x  # 经度
            lat = geom.y  # 纬度

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="geom 格式不正确，请传入合法的 WKT 格式"
            )

        # 只有 4326/4490 地理坐标系才校验经纬度范围
        if coord_sys in (4326, 4490):
            if not (-180 <= lon <= 180):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="geom 中的经度必须在 -180 ~ 180 之间"
                )

            if not (-90 <= lat <= 90):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="geom 中的纬度必须在 -90 ~ 90 之间"
                )

        return values



    # model_config = ConfigDict(from_attributes=True)

class PointUpdate(BaseModel):
    """更新点位入参"""
    name: str | None = Field(None, min_length=1, max_length=100, description="点位名称")
    address: str | None = Field(None, max_length=255, description="点位地址")
    geom: str | None = Field(
        None,
        pattern=r"^POINT\(\d+\.?\d* \d+\.?\d*\)$",
        description="WKT格式点位",
        examples=["POINT(120.0 30.0)"]
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
            geom = loads(geom_wkt)

            lon = geom.x  # 经度
            lat = geom.y  # 纬度
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="geom 格式不正确，请传入合法的 WKT 格式"
            )

        # 只有 4326/4490 地理坐标系才校验经纬度范围
        if coord_sys in (4326, 4490):
            if not (-180 <= lon <= 180):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="geom 中的经度必须在 -180 ~ 180 之间"
                )

            if not (-90 <= lat <= 90):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="geom 中的纬度必须在 -90 ~ 90 之间"
                )

        return values

    # model_config = ConfigDict(from_attributes=True)


# ------------------------------
# 出参模型
# ------------------------------

class Geometry(BaseModel):
    type: str
    coordinates: Any

class Properties(BaseModel):
    id: int
    userid: int
    name: str
    address: str | None = None
    coord_sys: int = 4326
    create_time: str | None = None
    update_time: str | None = None

class PointDetail(BaseModel):
    """点位详情出参"""
    type : str
    geometry : Geometry
    properties: Properties

    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM对象属性取值
    )


