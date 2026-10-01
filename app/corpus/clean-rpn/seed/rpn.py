def rpn(expr):
    stack = []
    for tok in expr.split():
        if tok == "+":
            b, a = stack.pop(), stack.pop()
            stack.append(a + b)
        else:
            stack.append(float(tok))
    return stack[0]
