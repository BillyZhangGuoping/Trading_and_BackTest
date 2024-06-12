def merge_dicts_with_new_keys(dicts):
    result = {}
    index = 0
    for d in dicts:
        for key, value in d.items():
            if key in result:
                new_key = f"{key}_{index}"
                result[new_key] = value
                index += 1
            else:
                result[key] = value
    return result
