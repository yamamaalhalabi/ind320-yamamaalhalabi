import pandas as pd
import requests
from river import linear_model, preprocessing, time_series

BASE = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"


def load_fill_series(omr_type="EL", omrnr=3):
    """Weekly fill ratio for one Magasinstatistikk area (NO 0, EL 1-5, VASS 1-4)."""
    resp = requests.get(f"{BASE}/HentOffentligData", timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df = df[(df["omrType"] == omr_type) & (df["omrnr"] == omrnr)].copy()
    df["date"] = pd.to_datetime(df["dato_Id"])
    series = df.drop_duplicates("date").set_index("date")["fyllingsgrad"].sort_index()
    series.name = "fill_ratio"
    return series


def make_model(p=1, d=1, q=1, sp=0, sd=0, sq=0, m=1, lr=0.01):
    """River SNARIMAX with a standardised linear regressor trained by SGD."""
    from river import optim

    regressor = preprocessing.StandardScaler() | linear_model.LinearRegression(
        optimizer=optim.SGD(lr), intercept_lr=lr
    )
    return time_series.SNARIMAX(
        p=p, d=d, q=q, m=m, sp=sp, sd=sd, sq=sq, regressor=regressor
    )


def _week_of_year(index):
    return index.isocalendar().week.astype(int)


def forecast(series, horizon=12, history_weeks=260, p=1, d=1, q=1,
             sp=0, sd=0, sq=0, m=1, lr=0.01, exog=None):
    """Train an online SNARIMAX on the last `history_weeks` weeks and forecast `horizon` weeks.

    exog: optional DataFrame indexed by date (weekly) with exogenous columns. The future
    values of these are not known, so the mean of the same week of the year is used.
    """
    s = series.iloc[-history_weeks:]
    model = make_model(p, d, q, sp, sd, sq, m, lr)

    climatology = None
    if exog is not None and not exog.empty:
        climatology = exog.groupby(_week_of_year(exog.index)).mean()

    for date, y in s.items():
        x = None
        if exog is not None and not exog.empty:
            row = exog.reindex([date], method="nearest", tolerance=pd.Timedelta("3D"))
            x = row.iloc[0].fillna(0).to_dict()
        model.learn_one(y, x)

    future = pd.date_range(s.index[-1] + pd.Timedelta(days=7), periods=horizon, freq="7D")
    xs = None
    if climatology is not None:
        weeks = _week_of_year(future)
        xs = [climatology.reindex([w]).iloc[0].fillna(0).to_dict() for w in weeks]

    values = model.forecast(horizon, xs=xs)
    return pd.Series(values, index=future, name="forecast")


def backtest(series, horizon=12, **kwargs):
    """Hide the last `horizon` weeks, forecast them and compare with the truth."""
    train, actual = series.iloc[:-horizon], series.iloc[-horizon:]
    exog = kwargs.get("exog")
    fc = forecast(train, horizon=horizon, **kwargs)
    fc.index = actual.index  # same dates as the real weeks
    mae = (fc - actual).abs().mean()
    return fc, actual, mae