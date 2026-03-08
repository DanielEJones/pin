from src import lex, parse, run

from sys import argv


def main():
    if len(argv) < 2:
        print("Expected a file path to interpret.")
        return

    interpret(argv[1])


def interpret(path):
    with open(path, "r") as f:
        source = f.read()

    tokens = lex(source)
    if tokens is None:
        print("Failed to lex source")
        return

    tree = parse(tokens)
    if tree is None:
        print("Failed to parse source")
        return

    result = run(tree)
    print(result)


if __name__ == "__main__":
    main()
