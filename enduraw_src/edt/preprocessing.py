"""
| Module used to preprocess results
"""

import polars as pl


def remove_athletes_same_name(df_results):
    """
    Remove athletes that have the same name (all are removed)
    """

    df_results_pp = (
        df_results.with_columns(pl.col("result").count().over("name").alias("n_names"))
        .filter(pl.col("n_names") == 1)
        .drop(["n_names"])
    )

    return df_results_pp


def transform_splits_to_unique_row_athlete(df_splits_athlete):
    """
    Transform splits dataframe into an unique row dataframe
    Each column gives the split/total time at each split
    + a column for athlete name
    """

    df_splits_athlete_row = (
        df_splits_athlete.with_columns(pl.col("split").str.to_lowercase())
        .pivot("split", index="athlete_name", values=["time_split", "time_total"])
        .rename({"athlete_name": "name"})
    )

    return df_splits_athlete_row


def add_splits(df_results):
    """
    Add split times of each athlete to dataframe of results
    """

    ##Iterate through athletes
    data = []
    for athlete_name in df_results["name"]:
        ##Load athlete's splits
        df_splits_athlete = pl.read_parquet(
            f"/Users/qdouzery/Desktop/enduraw/data/edt-2024_results/splits/df_splits_{athlete_name.replace('_', '-')}.parquet"
        )

        ##Transform dataframe into an unique row
        df_splits_athlete_row = transform_splits_to_unique_row_athlete(
            df_splits_athlete
        )

        ##Aggregate data
        data.append(df_splits_athlete_row)

    ##Concat split times of all athletes into one dataframe
    df_splits_athletes = pl.concat(data)

    ##Merge split times to results dataframe
    df_results_splits = df_results.join(df_splits_athletes, on="name", how="left")

    return df_results_splits


def get_split_names():
    """
    Get all split names
    """

    df_splits_athlete = pl.read_parquet(
        "/Users/qdouzery/Desktop/enduraw/data/edt-2024_results/splits/df_splits_adam-okarmus.parquet"
    )
    df_splits_athlete_row = transform_splits_to_unique_row_athlete(df_splits_athlete)
    list_split_names = [
        col
        for col in df_splits_athlete_row.columns
        if col not in ["name", "time_total_finish"]
    ]

    return list_split_names


def compute_rank_splits(df_results_splits, list_split_names):
    """
    For each athlete, compute the rank on each split
    """

    list_col = []
    for aux_split in list_split_names:
        split = aux_split.replace("time_", "")
        list_col.append(pl.col(aux_split).rank(method="min").alias(f"rank_{split}"))
    df_results_splits_pp = df_results_splits.with_columns(list_col)

    return df_results_splits_pp


def convert_times(df_results_splits):
    """
    Convert all time columns from time object to a number of seconds
    """

    ##Get all time columns
    list_col_times = [col for col in df_results_splits.columns if "time" in col]

    ##Convert all time columns into a number of seconds
    list_col_times_pp = []
    for col_time in list_col_times:
        list_col_times_pp.append(
            pl.col(col_time).cast(pl.Duration()).dt.total_seconds().alias(col_time),
        )
    df_results_splits_pp = df_results_splits.with_columns(list_col_times_pp)

    return df_results_splits_pp


def transform_sex_dummies(df_results_splits):
    """
    Transform categorical 'sex' variable into dummies (1 & 0 for 'sex_F' & 'sex_M')
    """

    dummies_sex = df_results_splits["sex"].to_dummies()
    df_results_splits_pp = df_results_splits.with_columns(dummies_sex)

    return df_results_splits_pp


def preprocess_results(df_results):
    """
    Preprocess results:
        - Add split times
        - Drop missing values
        - Compute ranking at each split
        - Convert time columns
        - Transform sex variable into dummies
    """

    ##Remove athletes with the same name
    df_results = remove_athletes_same_name(df_results)

    ##Add split times to results dataframe
    df_results_splits = add_splits(df_results)

    ##Drop any athlete with at least one missing value
    df_results_splits = df_results_splits.drop_nulls().sort("time")

    ##Compute rank at each split
    list_split_names = get_split_names()
    df_results_splits = compute_rank_splits(df_results_splits, list_split_names)

    ##Compute final results without missing athletes
    df_results_splits = df_results_splits.with_columns(
        pl.col("time").rank(method="min").alias("rank_total_finish"),
    )

    ##Convert time columns
    df_results_splits = convert_times(df_results_splits)

    ##Transform sex into dummies
    df_results_splits = transform_sex_dummies(df_results_splits)

    ##Save preprocessed results
    df_results_splits.write_parquet(
        "/Users/qdouzery/Desktop/enduraw/data/edt-2024_results/df_results_splits.parquet"
    )

    return df_results_splits


if __name__ == "__main__":
    ##Load all results
    df_results = pl.read_parquet(
        "/Users/qdouzery/Desktop/enduraw/data/edt-2024_results/df_results.parquet"
    )

    ##Preprocess results
    df_results_splits = preprocess_results(df_results)
