def get_file_type(filename: str) -> str:

    name = filename.lower()  # 转小写，避免 .CSV / .XLSX 问题

    if name.endswith(('.xlsx', '.xls')):
        return 'excel'

    elif name.endswith('.csv'):
        return 'csv'

    else:
        return 'unknown'