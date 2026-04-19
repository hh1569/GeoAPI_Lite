from typing import List, Any

def to_feature_collection(features: List[Any]) -> dict:
    """将包含 to_geojson_feature 方法的对象列表转为 GeoJSON FeatureCollection"""
    return {
        "type": "FeatureCollection",
        "features": [f.to_geojson_feature() for f in features]
    }