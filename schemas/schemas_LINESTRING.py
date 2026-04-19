from datetime import datetime
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from starlette import status
from shapely.wkt import loads


class LinestringCreate(BaseModel):
    """创建线位入参"""
    name: str = Field(min_length=1, max_length=100, description="线位名称")
    address: str | None = Field(None, max_length=255, description="线位地址")
    geom: str = Field(
        pattern=r"^LINESTRING\(\d+\.?\d* \d+\.?\d*(?:, \d+\.?\d* \d+\.?\d*)+\)$",
        description="WKT格式线要素，例：LINESTRING(120 30, 121 31)",
        examples=["LINESTRING(120.0 30.0, 121.0 31.0)"]
    )

    @model_validator(mode="before")
    def check_geom_coords(cls, values):
        # 1. 取出 geom（和你原来一样）
        geom_wkt = values.get("geom")

        if not geom_wkt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="geom 不能为空"
            )

        try:
            # 2. 解析 WKT → 支持 点、线、面（和你一样）
            geom = loads(geom_wkt)

            # 3. 获取所有坐标点
            all_coords = list(geom.coords)#coords用来获取所有坐标点的工具

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="geom 格式不正确，请传入合法的 WKT 格式"
            )

        # 4. 遍历所有点，每个点都校验经纬度
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
    name: str | None = Field(None, min_length=1, max_length=100, description="点位名称")
    address: str | None = Field(None, max_length=255, description="点位地址")
    geom: str | None = Field(
        None,
        pattern=r"^LINESTRING\(\d+\.?\d* \d+\.?\d*(?:, \d+\.?\d* \d+\.?\d*)+\)$",
        description="WKT格式线要素",
        examples=["LINESTRING(120.0 30.0, 121.0 31.0)"]
    )

    @model_validator(mode="before")
    def check_geom_coords(cls, values):
        # 1. 取出 geom（和你原来一样）
        geom_wkt = values.get("geom")
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

        # 4. 遍历所有点，每个点都校验经纬度
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
    address: str =  None
    create_time: str = None
    update_time: str = None

class LinestringDetail(BaseModel):
    """点位详情出参"""
    type : str
    geometry : Geometry
    properties: Properties

    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM对象属性取值
    )


