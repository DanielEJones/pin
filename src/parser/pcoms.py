def has_more(tokens, start):
    return start < len(tokens)


def is_exhausted(tokens, start):
    if has_more(tokens, start):
        return start, None

    return start, "EoF"


def expect_kind(tokens, start, kind):
    if not has_more(tokens, start):
        return start, None

    got, lex = tokens[start]
    new_pos = start + 1

    if kind == got:
        return new_pos, lex

    return start, None


def expect_lexeme(tokens, start, lexeme):
    if not has_more(tokens, start):
        return start, None

    _, got = tokens[start]
    new_pos = start + 1

    if lexeme == got:
        return new_pos, lexeme

    return start, None


def sequence(tokens, start, parsers):
    pos = start

    results = []
    for parser in parsers:
        pos, result = run_parser(tokens, pos, parser)
        if result is None:
            return start, None

        results.append(result)

    return pos, results

    # def go(items, pos, results):
    #     if not items:
    #         return pos, results
    #
    #     first, *rest = items
    #     new_pos, result = run_parser(tokens, pos, first)
    #     if result is None:
    #         return start, None
    #
    #     results.append(result)
    #     return go(rest, new_pos, results)
    #
    # return go(parsers, start, [])


def choice(tokens, start, options):
    for (parser, *args) in options:
        pos, result = parser(tokens, start, *args)
        if result is not None:
            return pos, result

    return start, None


def zero_or_more(tokens, start, parser):
    parser, *args = parser
    pos = start

    results = []
    while has_more(tokens, pos):
        pos, result = parser(tokens, pos, *args)
        if result is None:
            break
        results.append(result)

    return pos, results


def one_or_more(tokens, start, parser):
    pos, result = zero_or_more(tokens, start, parser)
    if result is None or len(result) < 1:
        return start, None

    return pos, result


def optional(tokens, start, subparser, default):
    pos, result = run_parser(tokens, start, subparser)
    if result is None:
        return start, default

    return pos, result


def surrounded_by(tokens, start, opening, middle, closing):
    parser = (sequence, [opening, middle, closing])

    pos, result = run_parser(tokens, start, parser)
    if result is None:
        return start, None

    [_, value, _] = result
    return pos, value


def separated_by(tokens, start, separator, subparser):
    parser = (sequence, [subparser, (zero_or_more, (sequence, [separator, subparser]))])

    pos, result = run_parser(tokens, start, parser)
    if result is None:
        return start, None

    [first, rest] = result
    return pos, [first, *[e[1] for e in rest]]


def apply(tokens, start, parser, function):
    pos, result = run_parser(tokens, start, parser)
    if result is None:
        return start, None

    return pos, function(result)


def tagged(tokens, start, parser, tag):
    pos, result = run_parser(tokens, start, parser)
    if result is None:
        return start, None

    return pos, (tag, result)


def replace(tokens, start, parser, value):
    pos, result = run_parser(tokens, start, parser)
    if result is None:
        return start, None

    return pos, value


def run_parser(tokens, start, parser):
    parser, *args = parser
    return parser(tokens, start, *args)


# ---------------------------------------------------------------------------------------------------------------------


def parse_binary_op(tokens, start, lower_parser, ops):
    parser = (sequence, [
        lower_parser,
        (zero_or_more, (sequence, [
            (choice, ops),
            lower_parser
        ]))
    ])

    pos, result = run_parser(tokens, start, parser)
    if result is None:
        return start, None

    [left, apps] = result
    for (op, right) in apps:
        left = (op, left, right)

    return pos, left


def parse_unary_op(tokens, start, lower_parser, ops):
    parser = (sequence, [
        (zero_or_more, (choice, ops)),
        lower_parser,
    ])

    pos, result = run_parser(tokens, start, parser)
    if result is None:
        return start, None

    [apps, value] = result
    for op in reversed(apps):
        value = (op, value)

    return pos, value


def parse_postfix_op(tokens, start, lower_parser, ops):
    parser = (sequence, [
        lower_parser,
        (zero_or_more, (choice, ops))
    ])

    pos, result = run_parser(tokens, start, parser)
    if result is None:
        return start, None

    [value, apps] = result
    for (tag, args) in apps:
        value = (tag, value, args)

    return pos, value
