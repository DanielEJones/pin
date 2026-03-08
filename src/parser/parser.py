from parser.pcoms import (
    sequence, choice, tagged, replace, optional,
    surrounded_by, separated_by, is_exhausted,
    expect_kind, expect_lexeme, run_parser,
    parse_binary_op, parse_unary_op, parse_postfix_op
)


def parse(tokens):
    _, result = sequence(tokens, 0, [
        (parse_expression, ),
        (is_exhausted, ),
    ])

    if result is None:
        return None

    [result, _] = result
    return result


def parse_expression(tokens, start):
    return parse_or(tokens, start)


def parse_or(tokens, start):
    return parse_binary_op(tokens, start, (parse_and, ), [(expect_lexeme, "or")])


def parse_and(tokens, start):
    return parse_binary_op(tokens, start, (parse_not, ), [(expect_lexeme, "and")])


def parse_not(tokens, start):
    return parse_unary_op(tokens, start, (parse_comp, ), [(expect_lexeme, "not")])


def parse_comp(tokens, start):
    return parse_binary_op(tokens, start, (parse_term, ), [
        (replace, (expect_lexeme, "<"), "lt"),
        (replace, (expect_lexeme, ">"), "gt"),
        (replace, (expect_lexeme, "<="), "lte"),
        (replace, (expect_lexeme, ">="), "gte"),
        (replace, (expect_lexeme, "!="), "neq"),
        (replace, (expect_lexeme, "=="), "eq"),
    ])


def parse_term(tokens, start):
    return parse_binary_op(tokens, start, (parse_factor, ), [
        (replace, (expect_lexeme, "+"), "add"),
        (replace, (expect_lexeme, "-"), "sub"),
    ])


def parse_factor(tokens, start):
    return parse_binary_op(tokens, start, (parse_unary, ), [
        (replace, (expect_lexeme, "*"), "mul"),
        (replace, (expect_lexeme, "/"), "div"),
        (replace, (expect_lexeme, "%"), "mod"),
    ])


def parse_unary(tokens, start):
    return parse_unary_op(tokens, start, (parse_postfix, ), [
        (replace, (expect_lexeme, "-"), "neg"),
    ])


def parse_postfix(tokens, start):
    return parse_postfix_op(tokens, start, (parse_primary, ), [
        (tagged, (parse_call, ), "call"),
        (tagged, (parse_index, ), "index"),
    ])


def parse_call(tokens, start):
    return surrounded_by(tokens, start, (expect_lexeme, "("), (parse_arg_list, ), (expect_lexeme, ")"))


def parse_index(tokens, start):
    return surrounded_by(tokens, start, (expect_lexeme, "["), (parse_expression, ), (expect_lexeme, "]"))


def parse_arg_list(tokens, start):
    return separated_by(tokens, start, (expect_lexeme, ","), (parse_expression, ))


def parse_primary(tokens, start):
    return choice(tokens, start, [
        (parse_list, ),
        (parse_ident, ),
        (parse_number, ),
        (parse_string, ),
        (parse_boolean, ),
        (parse_grouping, ),
        (parse_if, ),
        (parse_let, ),
        (parse_lambda, ),
    ])


def parse_list(tokens, start):
    parser = (surrounded_by, (expect_lexeme, "["), (optional, (parse_arg_list,), []), (expect_lexeme, "]"))
    return tagged(tokens, start, parser, "list")


def parse_ident(tokens, start):
    return tagged(tokens, start, (expect_kind, "ident"), "var")


def parse_number(tokens, start):
    return tagged(tokens, start, (expect_kind, "number"), "num")


def parse_string(tokens, start):
    return tagged(tokens, start, (expect_kind, "string"), "str")


def parse_boolean(tokens, start):
    return tagged(tokens, start, (choice, [(expect_lexeme, "true"), (expect_lexeme, "false")]), "bool")


def parse_grouping(tokens, start):
    return surrounded_by(tokens, start, (expect_lexeme, "("), (parse_expression, ), (expect_lexeme, ")"))


def parse_if(tokens, start):
    parser = (sequence, [
        (expect_lexeme, "if"), (parse_expression, ),
        (expect_lexeme, "then"), (parse_expression, ),
        (expect_lexeme, "else"), (parse_expression, ),
    ])

    pos, result = run_parser(tokens, start, parser)
    if result is None:
        return start, None

    [_, cond, _, body, _, els] = result
    return pos, ("if", cond, body, els)


def parse_let(tokens, start):
    parser = (sequence, [
        (expect_lexeme, "let"), (expect_kind, "ident"), (optional, (parse_params, ), []),
        (expect_lexeme, "="), (parse_expression, ),
        (expect_lexeme, ";"), (parse_expression, ),
    ])

    pos, result = run_parser(tokens, start, parser)
    if result is None:
        return start, None

    [_, name, args, _, value, _, cont] = result
    if len(args) > 0:
        return pos, ("bind-fn", name, args, value, cont)

    return pos, ("bind", name, value, cont)


def parse_params(tokens, start):
    return surrounded_by(tokens, start, (expect_lexeme, "("), (parse_param_list, ), (expect_lexeme, ")"))


def parse_param_list(tokens, start):
    return separated_by(tokens, start, (expect_lexeme, ","), (expect_kind, "ident"))


def parse_lambda(tokens, start):
    parser = (sequence, [
        (expect_lexeme, "\\"), (parse_param_list, ),
        (expect_lexeme, "->"), (parse_expression, ),
    ])

    pos, result = run_parser(tokens, start, parser)
    if result is None:
        return start, None

    [_, args, _, body] = result
    return pos, ("lambda", args, body)
