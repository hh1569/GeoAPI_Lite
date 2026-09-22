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
        if lon is not None and not (-180 <= float(lon) <= 180):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="经度必须在 -180 ~ 180 之间"
            )

        if lat is not None and not (-90 <= float(lat) <= 90):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="纬度必须在 -90 ~ 90 之间"
            )

        return values


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

        if min_lon is not None and not (-180 <= float(min_lon) <= 180) or max_lon is not None and not (-180 <= float(max_lon) <= 180):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="经度必须在 -180 ~ 180 之间"
            )

        if min_lat is not None and not (-90 <= float(min_lat) <= 90) or max_lat is not None and not (-90 <= float(max_lat) <= 90):
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


class PoiAnalysisQuery(BaseModel):
    """POI 空间分析公共入参"""
    name_keyword: str | None = Field(default=None, description="按名称关键字过滤点位（模糊匹配），如 医院、餐饮")
    min_lon: float | None = Field(default=None, description="分析范围最小经度")
    min_lat: float | None = Field(default=None, description="分析范围最小纬度")
    max_lon: float | None = Field(default=None, description="分析范围最大经度")
    max_lat: float | None = Field(default=None, description="分析范围最大纬度")

    @model_validator(mode="after")
    def check_bbox(self):
        vals = [self.min_lon, self.min_lat, self.max_lon, self.max_lat]
        if any(v is not None for v in vals):
            if any(v is None for v in vals):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="分析范围需同时提供 min_lon、min_lat、max_lon、max_lat"
                )
            if self.min_lon >= self.max_lon or self.min_lat >= self.max_lat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="分析范围 min 值必须小于 max 值"
                )
        return self


class KdeQuery(PoiAnalysisQuery):
    """核密度分析入参"""
    grid_size: int = Field(default=60, ge=20, le=150, description="格网行列数（生成 N×N 个格网单元）")
    bandwidth: float | None = Field(default=None, gt=0, description="核密度带宽（米），不传自动取分析范围最大跨度的 1/30")


class KmeansQuery(PoiAnalysisQuery):
    """K均值空间聚类入参"""
    k: int = Field(default=5, ge=2, le=30, description="聚类数量")

