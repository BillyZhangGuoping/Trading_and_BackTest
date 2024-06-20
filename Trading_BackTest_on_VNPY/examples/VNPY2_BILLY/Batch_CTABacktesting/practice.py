dict1 = {'key1': 'value1', 'key2': 'value2', 'key3': 'value1', 'key4': 'value3'}
dict2 = {}

for key, value in dict1.items():
    if value not in dict2:
        dict2[value] = []
    dict2[value].append(key)

print(dict2)