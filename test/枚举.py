from enum import Enum

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3
    RRR = 1#被认为是RED别名

# 1. 访问成员
print(Color.RED)            # Color.RED
print(Color.RED.name)       # 'RED'
print(Color.RED.value)      # 1

# 2. 通过值获取成员
print(Color(2))             # Color.GREEN

# 3. 通过名称字符串获取成员（字典式访问）
print(Color['BLUE'])        # Color.BLUE

# 4. 遍历所有成员
for color in Color:
    print(color)
# 输出：
# Color.RED
# Color.GREEN
# Color.BLUE