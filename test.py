import pandas as pd

def concat_account_info(file_path : str) -> pd.DataFrame:
    df = pd.read_json(file_path, lines=True)
    df['posts'] = df['stats'].apply(lambda x: x.get('posts') if isinstance(x, dict) else None)
    df["followers"] = df["stats"].apply(lambda x: x.get("followers") if isinstance(x, dict) else None)
    df["following"] = df["stats"].apply(lambda x: x.get("following") if isinstance(x, dict) else None)
    df["num_link"] = df["externalLinks"].apply(lambda x: len(x) if isinstance(x, list) else None)
    return df

