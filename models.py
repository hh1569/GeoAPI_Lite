from datetime import datetime
from typing import Optional

from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Index, Integer, ForeignKey, DateTime
from geoalchemy2 import Geometry
from database import Base

#用户表
class User(Base):
    __tablename__ = "User"

    userid: Mapped[int] = mapped_column(primary_key=True,autoincrement=True, comment="⽤户ID")
    password :Mapped[str] = mapped_column(String(255),nullable=False,comment="密码")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="⽤户名")
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=False, comment="⼿机号")


#令牌表ORM模型
class UserToken(Base):
    __tablename__ = 'user_token'
    # 创建索

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement = True, comment = "令牌ID")
    userid: Mapped[int] = mapped_column(ForeignKey(User.userid), nullable = False, comment = "⽤户ID")
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="令牌值")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,comment="过期时间")


#点位表
class PointFeature(Base):
    __tablename__ = "point_feature"
    __table_args__ = (Index('idx_pois_geom', 'geom', postgresql_using='gist'),{"comment": "空间点位表"})


    # 业务字段
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="点位名称")
    id: Mapped[int] = mapped_column(primary_key=True, comment="主键ID")
    userid: Mapped[int] = mapped_column(ForeignKey(User.userid), nullable=False, comment="用户id")
    address: Mapped[str | None] = mapped_column(String(255), comment="点位地址")

    # GIS核心字段：POINT类型，4326坐标系（WGS84 GPS经纬度）
    geom: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
        comment="空间几何点位"
    )

    def get_wkt(self, geom_field: str):
        """获取几何的WKT文本格式（如 POINT(120 30)）"""
        geom = getattr(self, geom_field)
        return to_shape(geom).wkt

    def get_lon(self, geom_field: str) -> float:
        """获取经度（X坐标）"""
        geom = getattr(self, geom_field)
        return to_shape(geom).x

    def get_lat(self, geom_field: str) -> float:
        """获取纬度（Y坐标）"""
        geom = getattr(self, geom_field)
        return to_shape(geom).y

    def to_dict(self,geom_field):
        """转成前端可直接使用的字典（自动处理几何字段）"""
        return {
            "id": self.id,
            "userid": self.userid,
            "name": self.name,
            "address": self.address,
            "geom": self.get_wkt(geom_field),
            "lon": self.get_lon(geom_field),
            "lat": self.get_lat(geom_field),
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S") if self.create_time else None,
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S") if self.create_time else None
        }

    def to_geojson_feature(self) -> dict:
        """将要素转为标准 GeoJSON Feature 对象"""
        # to_shape 将一个 数据库几何对象（WKBElement 或 WKTElement）转换成 Shapely 几何对象。它不仅能处理 WKB，也能处理 WKT 格式的封装对象。
        # from_shape：将一个 Shapely 几何对象 转换成 WKBElement（即数据库可存储的 WKB 格式的封装对象）。
        from geoalchemy2.shape import to_shape,from_shape
        from shapely.geometry import mapping
        geom_shapely = to_shape(self.geom)
        geometry_dict = mapping(geom_shapely)  # 自动生成 {"type": "Point", "coordinates": [lon, lat]}

        return {
            "type": "Feature",
            "geometry": geometry_dict,
            "properties": {
                "id": self.id,
                "userid": self.userid,
                "name": self.name,
                "address": self.address,
                "create_time": self.create_time.isoformat() if self.create_time else None,
                "update_time": self.update_time.isoformat() if self.update_time else None,
            }
        }



#线位表
class LinestringFeature(Base):
    __tablename__ = "Linestring_feature"
    __table_args__ = (Index('idx_pois_geom', 'geom', postgresql_using='gist'),{"comment": "空间线位表"})


    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="线位名称")
    id: Mapped[int] = mapped_column(primary_key=True, comment="主键ID")
    userid: Mapped[int] = mapped_column(ForeignKey(User.userid), nullable=False, comment="用户id")
    address: Mapped[str | None] = mapped_column(String(255), comment="线位地址")

    geom: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326),
        nullable=False,
        comment="空间几何线位"
    )

    def get_wkt(self, geom_field: str) -> str:
        """获取几何的WKT文本格式（如 POINT(120 30)）"""
        #getattr(object, name[, default])
        # - object ：要获取属性的对象
        # - name ：属性的名称， 必须是字符串
        # - default ：可选参数，当属性不存在时返回的默认值

        geom = getattr(self, geom_field)
        return to_shape(geom).wkt

    def to_dict(self,geom_field):
        """转成前端可直接使用的字典（自动处理几何字段）"""
        return {
            "id": self.id,
            "userid": self.userid,
            "name": self.name,
            "address": self.address,
            "geom": self.get_wkt(geom_field),
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def to_geojson_feature(self) -> dict:
        """将要素转为标准 GeoJSON Feature 对象"""
        # 利用 geoalchemy2.shape.to_shape 将数据库几何转为 shapely 对象
        from geoalchemy2.shape import to_shape
        from shapely.geometry import mapping

        geom_shapely = to_shape(self.geom)
        geometry_dict = mapping(geom_shapely)  # 自动生成 {"type": "Point", "coordinates": [lon, lat]}

        return {
            "type": "Feature",
            "geometry": geometry_dict,
            "properties": {
                "id": self.id,
                "userid": self.userid,
                "name": self.name,
                "address": self.address,
                "create_time": self.create_time.isoformat() if self.create_time else None,
                "update_time": self.update_time.isoformat() if self.update_time else None,
            }
        }



#面位表
class PolygonFeature(Base):
    __tablename__ = "Polygon_feature"
    __table_args__ = (Index('idx_pois_geom', 'geom', postgresql_using='gist'),{"comment": "空间面位表"})


    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="面位名称")
    id: Mapped[int] = mapped_column(primary_key=True, comment="主键ID")
    userid: Mapped[int] = mapped_column(ForeignKey(User.userid), nullable=False, comment="用户id")
    address: Mapped[str | None] = mapped_column(String(255), comment="面位地址")

    geom: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=False,
        comment="空间几何面"
    )

    def get_wkt(self, geom_field: str) -> str:
        """获取几何的WKT文本格式（如 POINT(120 30)）"""
        geom = getattr(self, geom_field)
        return to_shape(geom).wkt

    def to_dict(self,geom_field):
        """转成前端可直接使用的字典（自动处理几何字段）"""
        return {
            "id": self.id,
            "userid": self.userid,
            "name": self.name,
            "address": self.address,
            "geom": self.get_wkt(geom_field),
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def to_geojson_feature(self) -> dict:
        """将要素转为标准 GeoJSON Feature 对象"""
        # 利用 geoalchemy2.shape.to_shape 将数据库几何转为 shapely 对象
        from geoalchemy2.shape import to_shape
        from shapely.geometry import mapping

        geom_shapely = to_shape(self.geom)
        geometry_dict = mapping(geom_shapely)  # 自动生成 {"type": "Point", "coordinates": [lon, lat]}

        return {
            "type": "Feature",
            "geometry": geometry_dict,
            "properties": {
                "id": self.id,
                "userid": self.userid,
                "name": self.name,
                "address": self.address,
                "create_time": self.create_time.isoformat() if self.create_time else None,
                "update_time": self.update_time.isoformat() if self.update_time else None,
            }
        }