
#-*-coding:utf-8-*-
# import pandas
#
# e = pandas.read_excel(r"C:\Users\hhh\Desktop\新建 Microsoft Excel 工作表.xlsx")
# print(e)
# t = e.columns
#
# d = e.to_dict(orient="records")
# print(d)
# for col in t:
#     print(col)

import magic

e = r"C:\Users\hhh\Desktop\新建 Microsoft Excel 工作表.csv"
file = open(e,'rb')
a = file.read()
# print(a)
import mimetypes


def get_file_type(filename: str) -> str:
    """
    正常人判断文件类型：只看后缀
    100% 能用，不报错，不折腾
    """
    name = filename.lower()  # 转小写，避免 .CSV / .XLSX 问题

    if name.endswith(('.xlsx', '.xls')):
        return 'excel'

    elif name.endswith('.csv'):
        return 'csv'

    else:
        return 'unknown'

print(get_file_type(e))
