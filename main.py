from src import interpret
from sys import argv, setrecursionlimit


def main():
    setrecursionlimit(100_000)

    if len(argv) < 2:
        print("Expected a file path to interpret.")
        return

    result = interpret(argv[1])
    print(result)


if __name__ == "__main__":
    main()
