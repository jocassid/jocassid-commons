

def normalize_whitespace(text_in):
    buffer = []
    is_leading_space = True
    for c in text_in:
        if c.isspace():
            if buffer and buffer[-1] != ' ':
                buffer.append(' ')
            continue
        if is_leading_space:
            is_leading_space = False
        buffer.append(c)
    if buffer and buffer[-1] == ' ':
        buffer.pop()
    return "".join(buffer)
