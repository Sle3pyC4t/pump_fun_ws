from pump_fun_py.pump_fun import buy


def buy_example(mint_str: str):
    sol_in = 0.01
    slippage = 50
    return buy(mint_str, sol_in, slippage)


if __name__ == "__main__":
    buy_example("5c1YgYzAf81qGmWU7aJ6Y2jhBnVw1q3wnK4r3wtPxA1M")