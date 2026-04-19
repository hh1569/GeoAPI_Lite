from datetime import datetime
from typing import Any
from shapely.wkt import loads
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from starlette import status

#数据校验数值错误时，无法进入判断，只会抛异常。。。没搞懂
class PolygonCreate(BaseModel):
    """创建面位入参"""
    name: str = Field(min_length=1, max_length=100, description="线位名称")
    address: str | None = Field(None, max_length=255, description="线位地址")
    geom: str = Field(
        pattern=r"^POLYGON\(\(\d+\.?\d* \d+\.?\d*(?:, \d+\.?\d* \d+\.?\d*)+\)\)$",
        description="WKT格式面要素，例：POLYGON((120 30, 121 30, 121 31, 120 30))",
        examples=["POLYGON((120.0 30.0, 121.0 30.0, 121.0 31.0, 120.0 30.0))"]
    )

    @model_validator(mode="before")
    def check_geom_coords(cls, values):
        # 1. 取出 geom
        geom_wkt = values.get("geom")

        if not geom_wkt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="geom 不能为空"
            )

        try:
            # 2. 解析 WKT,转为shape
            geom = loads(geom_wkt)

            # 3. 获取所有坐标点
            all_coords = list(geom.exterior.coords)  # exterior面外圈坐标，coords用来获取所有坐标点的工具

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="geom 格式不正确，请传入合法的 WKT 格式"
            )
        if all_coords[0] != all_coords[-1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="面必须首尾相连"
            )

        # 4. 遍历所有点，每个点都校验经纬度（和你原来逻辑一样）
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

class PolygonUpdate(BaseModel):
    """更新面位入参"""
    name: str | None = Field(None, min_length=1, max_length=100, description="点位名称")
    address: str | None = Field(None, max_length=255, description="点位地址")
    geom: str | None = Field(
        None,
        pattern=r"^POLYGON\(\(\d+\.?\d* \d+\.?\d*(?:, \d+\.?\d* \d+\.?\d*)+\)\)$",
        description="WKT格式点位",
        examples=["POLYGON((120.0 30.0, 121.0 30.0, 121.0 31.0, 120.0 30.0))"]
    )

    @model_validator(mode="before")
    def check_geom_coords(cls, values):
        # 1. 取出 geom
        geom_wkt = values.get("geom")
        if not geom_wkt:
            return values

        try:
            # 2. 解析 WKT → 支持 点、线、面（和你一样）
            geom = loads(geom_wkt)

            # 3. 获取所有坐标点
            all_coords = list(geom.exterior.coords)  # exterior面的外圈 / 外边界,coords用来获取所有坐标点的工具

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="geom 格式不正确，请传入合法的 WKT 格式"
            )
        if all_coords[0] != all_coords[-1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="面必须首尾相连"
            )

        # 4. 遍历所有点，每个点都校验经纬度（和你原来逻辑一样）
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

    # model_config = ConfigDict(from_attributes=True)


class Geometry(BaseModel):
    type: str
    coordinates: Any

class Properties(BaseModel):
    id: int
    userid: int
    name: str
    address: str =  None
    create_time: str = None
    update_time: str = None

class PolygonDetail(BaseModel):
    """点位详情出参"""
    type : str
    geometry : Geometry
    properties: Properties

    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM对象属性取值
    )