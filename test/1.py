class qq:
    a=1
a=qq()
setattr(qq,"a",'qq')#setattr 给对象赋值
print(qq.a)
setattr(a,"a","bb")
print(a.a)
# ///////////////////////////

#getattr(object, name[, default])# - object ：要获取属性的对象# - name ：属性的名称， 必须是字符串# - default ：可选参数，当属性不存在时返回的默认值
class Person:
    name = "小红"
p = Person()
# 1. 有这个属性：正常取
print(getattr(p, "name", "无名氏"))  # 输出：小红
# 2. 没有这个属性：用默认值
print(getattr(p, "age", "18"))  # 输出：18
