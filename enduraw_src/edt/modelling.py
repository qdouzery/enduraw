"""
| Module used to create models to predict finish rank
"""

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import LinearSVR
from lightgbm import LGBMRegressor


def select_var(df, list_var_x, var_y):
    """
    Select variables of interest
    """

    return df.select(list_var_x + [var_y])


def split_xy(df, list_var_x, var_y):
    """
    Split dataframe between X (features) and y (target)
    """

    df_x = df.select(list_var_x)
    df_y = df.select([var_y])

    return df_x, df_y


def init_model(model_name):
    """
    Initialize model
    """

    dict_name_model = {
        "linear_regression": LinearRegression(),
        "ridge_regression": Ridge(),
        "tree": DecisionTreeRegressor(),
        "random_forest": RandomForestRegressor(),
        "svm": LinearSVR(),
        "lgbm": LGBMRegressor(verbose=-1),
    }

    return dict_name_model[model_name]


def postprocess_pred(y_pred):
    """
    Postprocessing of predictions:
        - Round as integers
    """

    y_pred_pp = np.round(y_pred, 0)

    return y_pred_pp
