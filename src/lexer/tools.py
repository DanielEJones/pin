def to_each(function, items):
    def go(values, result):
        if len(values) == 0:
            return result

        first, *rest = values
        new_value = function(first)

        result.append(new_value)
        return go(rest, result)

    return go(items, [])


def reduce(function, init, items):
    def go(values, result):
        if len(values) == 0:
            return result

        first, *rest = values
        new_value = function(result, first)
        return go(rest, new_value)

    return go(items, init)


def keep_if(predicate, items):
    def go(values, result):
        if len(values) == 0:
            return result

        first, *rest = values
        if predicate(first):
            result.append(first)
            return go(rest, result)

        return go(rest, result)

    return go(items, [])


def partition(predicate, items):
    def go(values, current, result):
        if len(current) > 0 and len(values) == 0:
            result.append(current)
            return result

        elif len(values) == 0:
            return result

        first, *rest = values
        if len(current) > 0 and predicate(first):
            result.append(current)
            result.append([first])
            return go(rest, [], result)

        elif predicate(first):
            result.append([first])
            return go(rest, [], result)

        else:
            current.append(first)
            return go(rest, current, result)

    return go(items, [], [])


def discard_between(start, stop, items):
    def keep(values, result):
        if not values:
            return result

        first, *rest = values
        if first == start:
            return drop(rest, result)

        else:
            result.append(first)
            return keep(rest, result)

    def drop(values, result):
        if not values:
            return result

        first, *rest = values
        if first == stop:
            return keep(rest, result)

        else:
            return drop(rest, result)

    return keep(items, [])
