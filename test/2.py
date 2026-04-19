class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"
p = Point(1, 2)
print(p)
# <__main__.Point object at 0x7f8c1a2b3d30>  # 不友好的默认表示