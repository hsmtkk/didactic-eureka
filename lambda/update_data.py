import dataclasses
import enum
import logging
import os
import os.path
import urllib.parse
import urllib.request

import aws_xray_sdk.core
import boto3
import bs4
import pandas

aws_xray_sdk.core.patch_all()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

JPX_URL_PREFIX = "https://www.jpx.co.jp"
JPX_INDEX_PATH = "/markets/derivatives/settlement-price/index.html"
NAMESPACE = "didactic-eureka"


class PUT_CALL(enum.StrEnum):
    PUT = "PUT"
    CALL = "CALL"

    def jpx_str(self) -> str:
        if self == PUT_CALL.PUT:
            return "PUT"
        else:
            return "CAL"


@dataclasses.dataclass
class OptionData:
    first_month_atm: int
    second_month_atm: int
    first_month_put_iv: float
    first_month_call_iv: float
    second_month_put_iv: float
    second_month_call_iv: float


def handler(event, context):
    logger.info("event", extra=event)
    csv_link = get_csv_link()
    csv_path = download_csv(csv_link)
    parse_csv(csv_path)


def get_csv_link() -> str:
    with urllib.request.urlopen(JPX_URL_PREFIX + JPX_INDEX_PATH) as f:
        html_content = f.read()
    soup = bs4.BeautifulSoup(html_content, "html.parser")
    a_tags = soup.find_all("a", href=True)
    for a_tag in a_tags:
        href = a_tag["href"]
        if ".csv" in href:
            return JPX_URL_PREFIX + href
    raise Exception("failed to find CSV in JPX site")


def download_csv(csv_link: str) -> os.PathLike:
    parsed = urllib.parse.urlparse(csv_link)
    filename = os.path.basename(parsed.path)
    csv_path = os.path.join("/tmp", filename)
    with urllib.request.urlopen(csv_link) as inf:
        with open(csv_path, "wb") as outf:
            outf.write(inf.read())
    return csv_path


def parse_csv(csv_path: os.PathLike):
    df = pandas.read_csv(csv_path, encoding="shift_jis", skiprows=2)
    print(df)
    (first_month_record, second_month_record) = get_first_second_month_record(df)
    first_month = first_month_record["限月"]
    second_month = first_month_record["限月"]
    first_month_atm = round250(first_month_record["清算価格"])
    second_month_atm = round250(second_month_record["清算価格"])
    first_month_put_iv = get_iv(df, PUT_CALL.PUT, first_month, first_month_atm)
    first_month_call_iv = get_iv(df, PUT_CALL.CALL, first_month, first_month_atm)
    second_month_put_iv = get_iv(df, PUT_CALL.PUT, second_month, second_month_atm)
    second_month_call_iv = get_iv(df, PUT_CALL.CALL, second_month, second_month_atm)
    option_data = OptionData(
        first_month_atm,
        second_month_atm,
        first_month_put_iv,
        first_month_call_iv,
        second_month_put_iv,
        second_month_call_iv,
    )
    logger.info("option data", extra=dataclasses.asdict(option_data))
    put_metric(option_data)


def get_first_second_month_record(
    df: pandas.DataFrame,
) -> tuple[pandas.Series, pandas.Series]:
    future_mini_df = df[df["銘柄名称"].str.startswith("FUT_225M_")]
    first_month_record = future_mini_df.iloc[0]
    second_month_record = future_mini_df.iloc[1]
    return (first_month_record, second_month_record)


def round250(value: float) -> int:
    return round(value / 250) * 250


def get_iv(df: pandas.DataFrame, put_call: PUT_CALL, month: str, atm: int) -> float:
    filtered_df = df[
        (df["PUT/CAL"] == put_call.jpx_str())
        & (df["限月"] == month)
        & (df["権利行使価格"] == atm)
        & (df["原資産名称"] == "日経225")
    ]
    return float(filtered_df["ボラティリティ"].iloc[0])


def put_metric(option_data: OptionData) -> None:
    data = [
        {
            "MetricName": "atm",
            "Dimensions": [
                {
                    "Name": "month",
                    "Value": "1",
                }
            ],
            "Values": [option_data.first_month_atm],
        },
        {
            "MetricName": "atm",
            "Dimensions": [
                {
                    "Name": "month",
                    "Value": "2",
                }
            ],
            "Values": [option_data.second_month_atm],
        },
        {
            "MetricName": "iv",
            "Dimensions": [
                {
                    "Name": "month",
                    "Value": "1",
                },
                {
                    "Name": "put_call",
                    "Value": "put",
                },
            ],
            "Values": [option_data.first_month_put_iv],
        },
        {
            "MetricName": "iv",
            "Dimensions": [
                {
                    "Name": "month",
                    "Value": "1",
                },
                {
                    "Name": "put_call",
                    "Value": "call",
                },
            ],
            "Values": [option_data.first_month_call_iv],
        },
        {
            "MetricName": "iv",
            "Dimensions": [
                {
                    "Name": "month",
                    "Value": "2",
                },
                {
                    "Name": "put_call",
                    "Value": "put",
                },
            ],
            "Values": [option_data.second_month_put_iv],
        },
        {
            "MetricName": "iv",
            "Dimensions": [
                {
                    "Name": "month",
                    "Value": "2",
                },
                {
                    "Name": "put_call",
                    "Value": "call",
                },
            ],
            "Values": [option_data.second_month_call_iv],
        },
    ]
    client = boto3.client("cloudwatch")
    client.put_metric_data(Namespace=NAMESPACE, MetricData=data)
