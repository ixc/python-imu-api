def clean_broken_json_text(text):
    """
    IMu fails to escape control characters in strings, so we need to traverse
    the strings contained within the JSON and manually escape them.
    """

    if isinstance(text, str):
        text_as_str = text
    else:
        text_as_str = text.decode("utf8")

    buf = str()
    within_string = False
    for i, char in enumerate(text_as_str):
        if char == '"':
            if within_string:
                if (
                    # Ignore escaped quotation marks within strings
                    text_as_str[i - 1] != "\\"
                    or
                    # Unless what looks like an escaped quotation mark is
                    # actually an escaped backslash
                    text_as_str[i - 2] == "\\"
                ) and (
                    # Detect the end of strings
                    text_as_str[i : i + 4] == '" : '
                    or text_as_str[i : i + 2] == '"\n'
                    or text_as_str[i : i + 3] == '",\n'
                    or text_as_str[i : i + 3] == '"\r\n'
                    or text_as_str[i : i + 4] == '",\r\n'
                ):
                    within_string = False
            else:
                within_string = True
        if within_string and char == "\n":
            buf += "\\n"
        elif within_string and char == "\t":
            buf += "\\t"
        elif within_string and char == "\b":
            buf += "\\b"
        elif within_string and char == "\f":
            buf += "\\f"
        elif within_string and char == "\r":
            buf += "\\r"
        else:
            buf += char

    return buf
