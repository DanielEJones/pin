from src.lexer import lex
from src.parser import parse


class Frame:
    def __init__(self, node, env):
        self.node = node
        self.env = env

        self.state = 0
        self.args = []
        self.fn = None

    def __repr__(self):
        return f"{self.node[0]} {self.node[1]}"


class Env:
    def __init__(self, parent, values):
        self.values = values
        self.parent = parent

    def find(self, name):
        if name in self.values:
            return self.values[name]

        if self.parent:
            return self.parent.find(name)

        return None, None


ARITH = {
    "add": lambda l, r: l + r,
    "sub": lambda l, r: l - r,
    "mul": lambda l, r: l * r,
    "div": lambda l, r: l / r,
    "mod": lambda l, r: l % r,
}
COMP = {
    "lt": lambda l, r: l < r,
    "gt": lambda l, r: l > r,
    "lte": lambda l, r: l <= r,
    "gte": lambda l, r: l >= r,
    "neq": lambda l, r: l != r,
    "eq": lambda l, r: l == r,
}


def better_run(tree, _):
    stack = []

    parent_frame = Frame(tree, Env(None, {}))
    stack.append(parent_frame)

    # Result of the previous computation stored here
    # after it's frame has been popped from the stack.
    result = (None, None)

    while len(stack) > 0:
        frame = stack[-1]
        command, *args = frame.node

        # LITERALS
        if command == "num":
            result = ("int", int(args[0]))
            stack.pop()

        elif command == "bool":
            result = ("bool", args[0] == "true")
            stack.pop()

        elif command == "list" and frame.state == 0:
            elements = args[0]
            elements_frame = Frame(("args-list", elements), frame.env)
            stack.append(elements_frame)
            frame.state = 1

        elif command == "list" and frame.state == 1:
            stack.pop()
            elements = result
            result = ("list", elements)

        elif command == "record" and frame.state == 0:
            elements = args[0]
            elements_frame = Frame(("args-list", elements), frame.env)
            stack.append(elements_frame)
            frame.state = 1

        elif command == "record" and frame.state == 1:
            stack.pop()
            key_values = result
            result = ("record", {key: value for item in key_values for key, value in item.items()})

        elif command == "field" and frame.state == 0:
            value_frame = Frame(args[1], frame.env)
            stack.append(value_frame)
            frame.state = 1

        elif command == "field" and frame.state == 1:
            stack.pop()
            name = args[0]
            value = result
            result = {name: value}

        elif command == "splat" and frame.state == 0:
            target = args[0]
            target_frame = Frame(target, frame.env)
            stack.append(target_frame)
            frame.state = 1

        elif command == "splat" and frame.state == 1:
            stack.pop()
            _, record = result
            result = record

        elif command == "var":
            var_name = args[0]
            result = frame.env.find(var_name)
            stack.pop()

        elif command == "call" and frame.state == 0:
            target_frame = Frame(args[0], frame.env)
            stack.append(target_frame)
            frame.state = 1

        elif command == "call" and frame.state == 1:
            frame.fn = result
            args_frame = Frame(("args-list", args[1]), frame.env)
            stack.append(args_frame)
            frame.state = 2

        elif command == "call" and frame.state == 2:
            stack.pop()
            _, params, body, captured_env = frame.fn
            args = result

            call_env = Env(captured_env, {param: arg for param, arg in zip(params, args)})
            call_frame = Frame(body, call_env)
            stack.append(call_frame)

        elif command == "access" and frame.state == 0:
            target = args[0]
            target_frame = Frame(target, frame.env)
            stack.append(target_frame)
            frame.state = 1

        elif command == "access" and frame.state == 1:
            stack.pop()
            field = args[1]
            _, record = result
            result = record[field]

        elif command == "index" and frame.state == 0:
            target = args[0]
            target_frame = Frame(target, frame.env)
            stack.append(target_frame)
            frame.state = 1

        elif command == "index" and frame.state == 1:
            list_value = result
            frame.args.append(list_value)

            index = args[1]
            index_frame = Frame(index, frame.env)
            stack.append(index_frame)
            frame.state = 2

        elif command == "index" and frame.state == 2:
            stack.pop()
            _, list_value = frame.args[0]
            _, index_value = result
            result = list_value[index_value]

        # CONSTRUCTS
        elif command == "bind" and frame.state == 0:
            value_frame = Frame(args[1], frame.env)
            stack.append(value_frame)
            frame.state = 1

        elif command == "bind" and frame.state == 1:
            stack.pop()
            bound_name = args[0]
            bound_value = result

            new_env = Env(frame.env, {bound_name: bound_value})
            new_frame = Frame(args[2], new_env)
            stack.append(new_frame)

        elif command == "bind-fn" and frame.state == 0:
            stack.pop()
            bound_name = args[0]
            params = args[1]
            body = args[2]

            new_env = Env(frame.env, {bound_name: ("closure", params, body, frame.env)})
            new_frame = Frame(args[3], new_env)
            stack.append(new_frame)

        elif command == "if" and frame.state == 0:
            condition_frame = Frame(args[0], frame.env)
            stack.append(condition_frame)
            frame.state = 1

        elif command == "if" and frame.state == 1:
            stack.pop()
            _, condition_value = result

            if condition_value:
                then_frame = Frame(args[1], frame.env)
                stack.append(then_frame)

            else:
                else_frame = Frame(args[2], frame.env)
                stack.append(else_frame)

        elif command == "lambda":
            params, body = args
            result = ("closure", params, body, frame.env)
            stack.pop()

        elif command == "args-list" and frame.state == 0:
            arguments = args[0]

            if len(arguments) < 1:
                result = frame.args
                stack.pop()

            else:
                head, *tail = arguments
                frame.node = ("args-list", tail)

                arg_frame = Frame(head, frame.env)
                stack.append(arg_frame)
                frame.state = 1

        elif command == "args-list" and frame.state == 1:
            frame.args.append(result)
            frame.state = 0

        # BINARY OPERATIONS
        elif command in ARITH and frame.state == 0:
            left_frame = Frame(args[0], frame.env)
            stack.append(left_frame)
            frame.state = 1

        elif command in ARITH and frame.state == 1:
            frame.args.append(result)
            right_frame = Frame(args[1], frame.env)
            stack.append(right_frame)
            frame.state = 2

        elif command in ARITH and frame.state == 2:
            _, left_number = frame.args[0]
            _, right_number = result
            result = ("int", ARITH[command](left_number, right_number))
            stack.pop()

        elif command in COMP and frame.state == 0:
            left_frame = Frame(args[0], frame.env)
            stack.append(left_frame)
            frame.state = 1

        elif command in COMP and frame.state == 1:
            frame.args.append(result)
            right_frame = Frame(args[1], frame.env)
            stack.append(right_frame)
            frame.state = 2

        elif command in COMP and frame.state == 2:
            _, left_number = frame.args[0]
            _, right_number = result
            result = ("bool", COMP[command](left_number, right_number))
            stack.pop()

        elif command == "neg" and frame.state == 0:
            value_frame = Frame(args[0], frame.env)
            stack.append(value_frame)
            frame.state = 1

        elif command == "neg" and frame.state == 1:
            _, value = result
            result = ("int", -value)
            stack.pop()

        elif command == "not" and frame.state == 0:
            value_frame = Frame(args[0], frame.env)
            stack.append(value_frame)
            frame.state = 1

        elif command == "not" and frame.state == 1:
            _, value = result
            result = ("bool", not value)
            stack.pop()

        elif command == "and" and frame.state == 0:
            left_frame = Frame(args[0], frame.env)
            stack.append(left_frame)
            frame.state = 1

        elif command == "and" and frame.state == 1:
            _, value = result
            if not value:
                result = ("bool", False)
                stack.pop()
                continue

            right_frame = Frame(args[1], frame.env)
            stack.append(right_frame)
            frame.state = 2

        elif command == "and" and frame.state == 2:
            stack.pop()

        elif command == "or" and frame.state == 0:
            left_frame = Frame(args[0], frame.env)
            stack.append(left_frame)
            frame.state = 1

        elif command == "or" and frame.state == 1:
            _, value = result
            if value:
                result = ("bool", True)
                stack.pop()
                continue

            right_frame = Frame(args[1], frame.env)
            stack.append(right_frame)
            frame.state = 2

        elif command == "or" and frame.state == 2:
            stack.pop()

        else:
            print(f"Unrecognized command {command!r}")
            return None, None

    return result


def interpret(path):
    with open(path, "r") as f:
        source = f.read()

    ast = frontend(source)
    if ast is None:
        print("Failed to parse source")
        return None

    result = better_run(ast, path)
    return result


def frontend(source):
    tokens = lex(source)
    if tokens is None:
        return None

    tree = parse(tokens)
    if tree is None:
        return None

    return tree


def run(ast, path):
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

        elif command == "record":
            items, = args

            record = {}
            for kind, *rest in items:
                if kind == "field":
                    name, value = rest
                    record[name] = go(value, env)

                elif kind == "splat":
                    other, = rest
                    ty, *data = go(other, env)
                    if ty != "record":
                        print(f"Cannot splat non record type {ty!r}")
                        return None, None

                    value, = data
                    record = {**record, **value}

            return "record", record

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

        elif command == "access":
            target, field = args

            ty, *data = go(target, env)
            if ty not in {"module", "record"}:
                print(f"Values of type {ty!r} do not have fields.")
                return None, None

            fields, = data
            return fields[field]

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

        "import": ("builtin", lambda *args: do_import(*args, path)),
        "export": ("builtin", do_export),
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


def do_import(*args):
    if len(args) != 2:
        print(f"Function 'import' only expects one argument, but {len(args) - 1} were provided.")
        return None, None

    (ty, *data), base_path = args
    if ty != "str":
        print(f"Could not call 'import' with type {ty!r}")
        return None, None

    path, = data

    actual_path = relative_to(path, base_path)
    result = interpret(actual_path)

    return result


def do_export(*args):
    module = {}

    for (ty, *data) in args:
        if not (ty == "list" and len(data := data[0]) == 2):
            print("Export must be called on [key, value] pairs.")
            return None, None

        [(key_ty, *key_data), value] = data
        if not (key_ty == "str"):
            print(f"Expected export key to be a string.")
            return None, None

        name, = key_data
        module[name] = value

    return "module", module


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


def relative_to(path, base_path):
    parts = base_path.split("/")
    parent_dir = "/".join(parts[:-1])
    return "/".join([parent_dir, path])
