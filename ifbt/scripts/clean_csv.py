def clean_csv(filename='Tyields', floats=slice(-11, None, None)):
    with open(f'../data/{filename}.txt', 'r') as f:
        contents = f.read()

    good, bad, ugly = [], [], []
    items = (line.split(',') for line in contents.strip().split('\n'))
    for item in items:
        try:
            clean = [int(item[0]),
                     *(-1 if it in ('', '#N/A') else float(it) for it in item[floats])]
            code = str(clean[0])
            statecode = int(code[:-6])
            cropcode = int(code[-3:-1])
            states = [1, 5, 12, 13, 17, 18, 19, 20, 21, 22, 24, 26, 27, 28,
                      29, 31, 37, 38, 39, 40, 41, 45, 46, 47, 48, 51, 54, 55]
            crops = [1, 2, 3]
            if statecode in states and cropcode in crops:
                good.append(clean)
            else:
                bad.append(clean)
        except ValueError:
            ugly.append(item)
    return good, bad, ugly


def save_clean(filename='Tyields', floats=slice(-11, None, None)):
    good, _, _ = clean_csv(filename, floats)
    contents = '\n'.join('\t'.join((str(it) for it in item)) for item in good)
    with open(f'../data/{filename}1.txt', 'w') as f:
        f.write(contents)

# save_clean('Tyields', slice(-11, None, None))
# save_clean('TA', slice(-7, -2, None))
# save_clean('coTAyields', slice(-32, -2, None))
# save_clean('FSAyields', slice(-12, -1, None))
