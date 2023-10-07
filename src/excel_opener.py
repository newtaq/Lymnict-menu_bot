import pandas as pd


def excel2dict(fileway: str):
    dataframe = pd.read_excel(fileway)

    df_dict = dataframe.to_dict()
    for category, values in df_dict.items():
        df_dict[category] = list(values.values())
        df_dict[category] = [i for i in df_dict[category] if isinstance(i, str)]
        
    return df_dict