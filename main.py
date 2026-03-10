from src import interpret
from sys import argv


def main():
    if len(argv) < 2:
        print("Expected a file path to interpret.")
        return

    result = interpret(argv[1])
    print(result)


if __name__ == "__main__":
    main()
