from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator
from starlette import status


class NearbyQuery(BaseModel):
    """附近点位查询入参"""
    lon: float = Field(description="中心点经度",examples=["-180 ~ 180"],ge=-180,le=180)
    lat: float = Field(description="中心点纬度",examples=["-90 ~ 90"],ge=-90,le=90)
    radius: float = Field(gt=0, description="查询半径（单位：米）", examples=[1000])

    @model_validator(mode="before")
    def check_coords(cls, values):
        # 取出参数
        lon = values.get("lon")
        lat = values.get("lat")

        # 手动判断 + 抛出自定义异常
        if lon is not None and not (-180 <= lon <= 180):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="经度必须在 -180 ~ 180 之间"
            )

        if lat is not None and not (-90 <= lat <= 90):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="纬度必须在 -90 ~ 90 之间"
            )

        return values

    # model_config = ConfigDict(from_attributes=True)

class BboxQuery(BaseModel):
    """矩形范围查询入参"""
    min_lon: float = Field(description="最小经度")
    min_lat: float = Field(description="最小纬度")
    max_lon: float = Field(description="最大经度")
    max_lat: float = Field(description="最大纬度")

    @model_validator(mode="before")
    def check_coords(cls, values):
        # 取出参数
        min_lon = values.get("min_lon")
        min_lat = values.get("min_lat")
        max_lon = values.get("max_lon")
        max_lat = values.get("max_lat")

        # 手动判断 + 抛出自定义异常
        if min_lon is not None and not (-180 <= min_lon <= 180) or max_lon is not None and not (-180 <= max_lon <= 180):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="经度必须在 -180 ~ 180 之间"
            )

        if min_lat is not None and not (-90 <= min_lat <= 90) or max_lat is not None and not (-90 <= max_lat <= 90):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="纬度必须在 -90 ~ 90 之间"
            )

        if min_lon >= max_lon:
            raise HTTPException(400, "最小经度不能大于等于最大经度")

        # 最小纬度 < 最大纬度
        if min_lat >= max_lat:
            raise HTTPException(400, "最小纬度不能大于等于最大纬度")

        return values

