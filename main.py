import argparse
import asyncio
import xml.etree.ElementTree as ET

import matplotlib
import matplotlib.dates as mdates

matplotlib.use("TkAgg")  ## <-  будет использовать tkinter для отрисовки графиков
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from aiohttp import ClientSession
from matplotlib.ticker import FuncFormatter, MaxNLocator

## XML_val.asp?d=0 <- код валют
## XML_dynamic.asp?date_req1=02/03/2001&date_req2=14/03/2001&VAL_NM_RQ=R01235 <- котировки динамика


def validate_and_format_dates(start_str: str, end_str: str) -> tuple[str, str]:
    """
    Принимает две даты в формате DD/MM/YYYY, проверяет их корректность,
    ограничения и возвращает отформатированные строки.

    Ограничения:
      - Начальная дата не раньше 01/01/2000
      - Конечная дата не позже сегодняшнего дня
      - Начальная дата не позже конечной

    :param start_str: начальная дата (строка DD/MM/YYYY)
    :param end_str: конечная дата (строка DD/MM/YYYY)
    :return: кортеж из двух строк (start, end) в формате DD/MM/YYYY
    :raises ValueError: при некорректном формате или нарушении ограничений
    """
    DATE_FORMAT = "%d/%m/%Y"
    MIN_DATE = datetime(2000, 1, 1)
    TODAY = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        start_dt = datetime.strptime(start_str, DATE_FORMAT)
    except ValueError:
        raise ValueError(
            f"Начальная дата '{start_str}' не соответствует формату DD/MM/YYYY"
        )

    try:
        end_dt = datetime.strptime(end_str, DATE_FORMAT)
    except ValueError:
        raise ValueError(
            f"Конечная дата '{end_str}' не соответствует формату DD/MM/YYYY"
        )

    if start_dt < MIN_DATE:
        raise ValueError(
            f"Начальная дата ({start_str}) не может быть раньше 01/01/2000"
        )

    if end_dt > TODAY:
        raise ValueError(
            f"Конечная дата ({end_str}) не может быть позже сегодняшнего дня "
            f"({TODAY.strftime(DATE_FORMAT)})"
        )

    if start_dt > end_dt:
        raise ValueError(
            f"Начальная дата ({start_str}) не может быть позже конечной ({end_str})"
        )

    return start_dt.strftime(DATE_FORMAT), end_dt.strftime(DATE_FORMAT)


def render_diogram(value: list, date: list):
    dates = mdates.date2num([datetime.strptime(d, "%d.%m.%Y") for d in date])
    values = [float(f.replace(",", ".")) for f in value]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(dates, values, color="#0058a3", linewidth=2)

    ax.set_title(
        f"Динамика цены долара за период с {date[0]} по {date[-1]}",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )
    ax.set_xlabel("Дата", fontsize=11, labelpad=10)
    ax.set_ylabel("Цена в руб.", fontsize=11, labelpad=10)

    ax.xaxis.set_major_locator(MaxNLocator(nbins=12))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y"))

    y_min, y_max = min(values), max(values)
    num_y_ticks = 8
    y_ticks = np.linspace(y_min, y_max, num_y_ticks)
    ax.set_yticks(y_ticks)

    def format_rub(value, pos):
        if abs(value - round(value)) < 0.001:
            return f"{int(value):,} ₽".replace(",", " ")
        else:
            return f"{value:,.2f} ₽".replace(",", " ")

    ax.yaxis.set_major_formatter(FuncFormatter(format_rub))

    ax.yaxis.set_major_locator(MaxNLocator(nbins=12))

    def format_coord(x, y):
        date_str = mdates.num2date(x).strftime("%d.%m.%Y")
        return f"Дата: {date_str}, Цена: {y:,.2f} руб.".replace(",", " ")

    ax.format_coord = format_coord

    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    plt.show()


async def get_data(sd: str, ed: str):
    date = []
    value = []

    async with ClientSession(base_url="https://www.cbr.ru/scripts/") as sessinn:
        async with sessinn.get(
            f"XML_dynamic.asp?date_req1={sd}&date_req2={ed}&VAL_NM_RQ=R01235"
        ) as response:
            try:
                tree = ET.fromstring(await response.text())
            except:
                return [], []

            for item in tree:
                try:
                    date.append(item.attrib["Date"])
                except:
                    continue

                try:
                    value.append(item[1].text)
                except:
                    value.append("")

    return date, value


async def main(sd: str, ed: str):
    date, value = await get_data(sd, ed)
    if (len(value) > 1) and (len(date) > 1):
        render_diogram(value, date)
    else:
        print("Мало данных для показа графика")
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Проверка и форматирование диапазона дат"
    )
    parser.add_argument("start", type=str, help="Начальная дата в формате DD/MM/YYYY")
    parser.add_argument("end", type=str, help="Конечная дата в формате DD/MM/YYYY")
    args = parser.parse_args()

    try:
        start_formatted, end_formatted = validate_and_format_dates(args.start, args.end)
        asyncio.run(main(start_formatted, end_formatted))
    except ValueError as err:
        print(f"Ошибка валидации: {err}")
        exit(1)
