from .__main__ import MetSel

app = MetSel


def main() -> None:
    app_instance = MetSel()
    app_instance.run()


if __name__ == "__main__":
    main()


