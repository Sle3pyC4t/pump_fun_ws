from pump_fun_py.pump_fun import sell


def sell_example(mint_str: str):
    percentage = 100
    slippage = 50
    sold = False
    while not sold:
        sold = sell(mint_str, percentage, slippage)


if __name__ == "__main__":
    # Sell Example
    sell_example("9DGkf5hAPcA2ak2SZFZyH1chyV2ZxvVcbp7WHJiGBAg9")