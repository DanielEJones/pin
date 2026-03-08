def run(ast):
    def go(node, env):
        command, *args = node
        if command is None:
            return None, None

        elif command == "num":
            val, = args
            return "int", int(val)

        elif command == "bool":
            val, = args
            return "bool", (val == "true")

        elif command == "str":
            val, = args
            return normalise_string(val)

        elif command == "list":
            val, = args
            return "list", [go(element, env) for element in val]

        elif command == "var":
            name, = args
            if name not in env:
                print(f"No such name {name!r} bound in scope.")
                return None, None

            var = env[name]
            return var

        elif command == "lambda":
            params, body = args

            closed_env = env.copy()
            closure = ("closure", params, body, closed_env)

            return closure

        elif command == "bind-fn":
            new_env = env.copy()
            cont = perform_recursive_bind(node, new_env)
            return go(cont, new_env)

        elif command == "bind":
            new_env = env.copy()
            cont = perform_recursive_bind(node, new_env)
            return go(cont, new_env)

        elif command == "call":
            target, args_list = args

            typ, *data = go(target, env)
            if typ not in {"closure", "builtin"}:
                if typ is not None:
                    print(f"Values of type {typ!r} is not callable: {target}.")
                return None, None

            if typ == "closure":
                params, body, closed_env = data

                call_env = closed_env.copy()
                for (param, arg) in zip(params, args_list):
                    call_env[param] = go(arg, env)

                return go(body, call_env)

            else:
                function, = data

                actual_args = []
                for arg in args_list:
                    new_arg = go(arg, env)
                    actual_args.append(new_arg)

                return function(*actual_args)

        elif command == "index":
            target, index = args
            return do_at(go(target, env), go(index, env))

        elif command == "if":
            cond, then, els = args

            typ, *data = go(cond, env)
            if typ != "bool":
                if typ is not None:
                    print(f"Values of type {typ!r} do not know truth.")
                return None, None

            cond_value, = data
            if cond_value:
                return go(then, env)

            else:
                return go(els, env)

        elif command in {"and", "or"}:
            left, right = args

            l_typ, *l_data = go(left, env)
            if l_typ != "bool":
                if l_typ is not None:
                    print(f"Values of type {l_typ!r} do not know truth.")
                return None, None

            r_typ, *r_data = go(right, env)
            if r_typ != "bool":
                if r_typ is not None:
                    print(f"Values of type {r_typ!r} do not know truth.")
                return None, None

            l_value, = l_data
            r_value, = r_data

            handler = {
                "and": lambda a, b: a and b,
                "or": lambda a, b: a or b,
            }[command]

            return "bool", handler(l_value, r_value)

        elif command == "not":
            target, = args

            typ, *data = go(target, env)
            if typ != "bool":
                if typ is not None:
                    print(f"Values of type {typ!r} do not know truth.")
                return None, None

            value, = data
            return "bool", not value

        elif command in {"lt", "gt", "lte", "gte"}:
            left, right = args

            l_typ, *l_data = go(left, env)
            if l_typ != "int":
                if l_typ is not None:
                    print(f"Values of type {l_typ!r} are incomparable.")
                return None, None

            r_typ, *r_data = go(right, env)
            if r_typ != "int":
                if r_typ is not None:
                    print(f"Values of type {r_typ!r} are incomparable.")
                return None, None

            l_value, = l_data
            r_value, = r_data

            handler = {
                "lt": lambda a, b: a < b,
                "gt": lambda a, b: a > b,
                "lte": lambda a, b: a <= b,
                "gte": lambda a, b: a >= b,
                "neq": lambda a, b: a != b,
                "eq": lambda a, b: a == b,
            }[command]

            return "bool", handler(l_value, r_value)

        elif command in {"eq", "neq"}:
            left, right = args

            handler = {
                "eq": lambda a, b: a == b,
                "neq": lambda a, b: a != b,
            }[command]

            l_val = go(left, env)
            r_val = go(right, env)
            return "bool", handler(l_val, r_val)

        elif command in {"add", "sub", "mul", "div", "mod"}:
            left, right = args

            l_typ, *l_data = go(left, env)
            if l_typ != "int":
                if l_typ is not None:
                    print(f"Values of type {l_typ} do not support arithmetic.")
                return None, None

            r_typ, *r_data = go(right, env)
            if r_typ != "int":
                if r_typ is not None:
                    print(f"Values of type {r_typ} do not support arithmetic.")
                return None, None

            l_value, = l_data
            r_value, = r_data

            handler = {
                "add": lambda a, b: a + b,
                "sub": lambda a, b: a - b,
                "mul": lambda a, b: a * b,
                "div": lambda a, b: a / b,
                "mod": lambda a, b: a % b,
            }[command]

            return "int", handler(l_value, r_value)

        elif command == "neg":
            target, = args

            typ, *data = go(target, env)
            if typ != "int":
                if typ is not None:
                    print(f"Values of type {typ} do not support arithmetic.")
                return None, None

            value, = data
            return "int", -value

        else:
            print(f"Unknown command {command}")
            return None, None

    def perform_recursive_bind(continuation, env):
        functions_to_be_bound = []
        values_to_be_bound = []

        (command, *args) = continuation

        while True:
            if command == "bind-fn":
                name, _, _, cont = args
                if name not in env:
                    env[name] = ("un-initialized",)

                functions_to_be_bound.append(args)
                (command, *args) = cont

            elif command == "bind":
                name, body, cont = args
                if name not in env:
                    env[name] = ("un-initialized",)

                values_to_be_bound.append(args)
                (command, *args) = cont

            else:
                break

        deepest_continuation = (command, *args)

        for (name, params, body, _) in functions_to_be_bound:
            closure = ("closure", params, body, env)
            env[name] = closure

        for (name, body, _) in values_to_be_bound:
            value = go(body, env)
            env[name] = value

        return deepest_continuation

    return go(ast, {
        "concat": ("builtin", do_concat),
        "append": ("builtin", do_append),
        "head": ("builtin", do_head),
        "tail": ("builtin", do_tail),
        "len": ("builtin", do_len),
        "at": ("builtin", do_at),

        "read_file": ("builtin", do_read_file),
        "write_file": ("builtin", do_write_file),
    })


def do_concat(*args):
    if len(args) != 2:
        print(f"Function 'concat' only expects two arguments, but {len(args)} were provided.")
        return None, None

    left, right = args
    l_ty, *l_data = left
    r_ty, *r_data = right

    if not (l_ty == r_ty) and l_ty in {"str", "list"}:
        print(f"Could not call 'concat' with types {l_ty!r} and {r_ty!r}.")
        return None, None

    l_value, = l_data
    r_value, = r_data

    return l_ty, l_value + r_value


def do_append(*args):
    if len(args) != 2:
        print(f"Function 'append' only expects two arguments, but {len(args)} were provided.")
        return None, None

    l, value = args
    l_ty, *l_data = l
    v_ty, *v_data = value

    if not l_ty == "list":
        print(f"Could not call 'append' with type {l_ty!r}.")
        return None, None

    l_value, = l_data
    v_value, = v_data

    return "list", [*l_value, (v_ty, v_value)]


def do_head(*args):
    if len(args) != 1:
        print(f"Function 'head' only expects one argument, but {len(args)} were provided.")
        return None, None

    (ty, *data), = args

    if not ty in {"str", "list"}:
        print(f"Could not call 'head' with type {ty!r}.")
        return None, None

    value, = data
    return annotate_with_type(value[0])


def do_tail(*args):
    if len(args) != 1:
        print(f"Function 'tail' only expects one argument, but {len(args)} were provided.")
        return None, None

    (ty, *data), = args

    if not ty in {"str", "list"}:
        print(f"Could not call 'tail' with type {ty!r}.")
        return None, None

    value, = data
    return ty, value[1:]


def do_len(*args):
    if len(args) != 1:
        print(f"Function 'len' only expects one argument, but {len(args)} were provided.")
        return None, None

    (ty, *data), = args

    if not ty in {"str", "list"}:
        print(f"Could not call 'len' with type {ty!r}.")
        return None, None

    value, = data
    return "int", len(value)


def do_at(*args):
    if len(args) != 2:
        print(f"Function 'at' only expects one argument, but {len(args)} were provided.")
        return None, None

    (l_ty, *l_data), (index_ty, *index_data) = args

    if not l_ty in {"str", "list"}:
        print(f"Could not call 'at' with type {l_ty!r}.")
        return None, None

    if not index_ty == "int":
        print(f"Could not call 'at' with type {index_ty!r}.")
        return None, None

    index, = index_data
    l, = l_data
    return annotate_with_type(l[index])


def do_read_file(*args):
    if len(args) != 1:
        print(f"Function 'read_file' only expected one argument, but {len(args)} were provided.")
        return None, None

    (ty, *data), = args

    if not ty == "str":
        print(f"Could not call 'read_file' with type {ty!r}")
        return None, None

    file_path, = data
    with open(file_path, "r") as f:
        contents = f.read()

    return "str", contents


def do_write_file(*args):
    if len(args) != 2:
        print(f"Function 'write_file' only expects two arguments, but {len(args)} were provided.")
        return None, None

    (path_ty, *path_data), (value_ty, *value_data) = args
    if not (path_ty == value_ty == "str"):
        print(f"Could not call 'write_file' with types {path_ty!r} and {value_ty!r}.")
        return None, None

    file_path, = path_data
    with open(file_path, "w") as f:
        value, = value_data
        f.write(value)

    return "nil",


def annotate_with_type(v):
    if isinstance(v, tuple):
        return v

    if isinstance(v, int) or isinstance(v, float):
        return "int", v

    elif isinstance(v, str):
        return "str", v

    elif isinstance(v, bool):
        return "bool", v

    elif isinstance(v, list):
        return "list", v

    else:
        print(f"happened! {v}")
        return None, None


def normalise_string(s):
    result = []
    escaped = False

    for ch in s[1:-1]:
        if ch == "\\" and not escaped:
            escaped = True

        elif escaped and ch == "n":
            result.append("\n")
            escaped = False

        elif escaped and ch == "t":
            result.append("\t")
            escaped = False

        elif escaped and ch == "\"":
            result.append("\"")
            escaped = False

        elif escaped and ch == "\\":
            result.append("\\")
            escaped = False

        elif escaped:
            print(f"Unrecognised escape sequence ending with {ch!r}.")
            return None, None

        else:
            result.append(ch)

    return "str", "".join(result)
