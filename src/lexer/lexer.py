from lexer.tools import partition, to_each, keep_if, reduce, discard_between


def lex(source):
    chunked_words = partition(is_separator, list(source))
    merged_words = reduce(merge_longer_ops, [], chunked_words)
    string_words = to_each("".join, merged_words)

    merged_strings = reduce(merge_strings, [], string_words)
    no_comments = discard_between("//", "\n", merged_strings)

    lexemes = keep_if(lambda s: not is_space(s), no_comments)
    tokens = to_each(construct_token, lexemes)

    errors = keep_if(is_error, tokens)
    if len(errors) > 0:
        to_each(print_error, errors)
        return None

    return tokens


def is_separator(ch):
    return is_symbol(ch) or is_space(ch)


def is_space(ch):
    return ch in {" ", "\t", "\n"}


def is_number(s):
    numbers = set("1234567890")
    return all(ch in numbers for ch in s)


def is_symbol(s):
    return all(ch in {
        "=", "!", "<", ">",
        "+", "-", "*", "/", "%",
        "(", ")", ";",
        "\\", ",", "\"",
        "[", "]"
    } for ch in s)


def is_ident(s):
    numbers = set("1234567890")
    alphabet = set("abcdefghijklmnopqrstuvwxyz_")

    first, *tail = s
    return (first in alphabet) and all(ch in numbers | alphabet for ch in tail)


def is_keyword(s):
    return s in {"or", "and", "not", "if", "then", "else", "let", "true", "false"}


def merge_longer_ops(elements, current):
    if not elements:
        elements.append(current)
        return elements

    *tail, top = elements
    if (top, current) == (["<"], ["="]):
        tail.append(["<", "="])
        return tail

    elif (top, current) == ([">"], ["="]):
        tail.append([">", "="])
        return tail

    elif (top, current) == (["="], ["="]):
        tail.append(["=", "="])
        return tail

    elif (top, current) == (["!"], ["="]):
        tail.append(["!", "="])
        return tail

    elif (top, current) == (["-"], [">"]):
        tail.append(["-", ">"])
        return tail

    elif (top, current) == (["/"], ["/"]):
        tail.append(["/", "/"])
        return tail

    else:
        tail.append(top)
        tail.append(current)
        return tail


def merge_strings(elements, current):
    if not elements:
        elements.append(current)
        return elements

    *tail, top = elements
    if is_incomplete_string(top):
        tail.append(top + current)
        return tail

    else:
        tail.append(top)
        tail.append(current)
        return tail


def is_incomplete_string(s):
    if not s.startswith("\""):
        return False

    if s.endswith("\""):
        return len(s) < 2 or s.endswith("\\\"")

    return True


def construct_token(lexeme):
    if is_number(lexeme):
        return "number", lexeme

    elif lexeme.startswith("\""):
        return "string", lexeme

    elif is_symbol(lexeme):
        return "symbol", lexeme

    elif is_keyword(lexeme):
        return "keyword", lexeme

    elif is_ident(lexeme):
        return "ident", lexeme

    return "error", lexeme


def is_error(token):
    typ, _ = token
    return typ == "error"


def print_error(token):
    _, lexeme = token
    print(f"Unrecognised token {lexeme!r}")
