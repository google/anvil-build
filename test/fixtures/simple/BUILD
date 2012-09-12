# Simple sample build file
# Does nothing but provide some rules

file_set('a',
     srcs=['a.txt'])

file_set('b',
    srcs=['b.txt'])

file_set('c',
    srcs=['c.txt'],
    deps=[':a', ':b'])

file_set('local_txt',
    srcs=glob('*.txt'))
file_set('recursive_txt',
    srcs=glob('**/*.txt'))
file_set('missing_txt',
    srcs='x.txt')
file_set('missing_glob_txt',
    srcs=glob('*.notpresent'))

file_set('local_txt_filter',
    srcs=glob('*'),
    src_filter='*.txt')
file_set('recursive_txt_filter',
    srcs=glob('**/*'),
    src_filter='*.txt')
file_set('exclude_txt_filter',
    srcs=glob('*'),
    src_exclude_filter='*.txt')
file_set('include_exclude_filter',
    srcs=glob('*'),
    src_filter='*.txt-a|*.txt-b',
    src_exclude_filter='*.txt')

file_set('file_input',
    srcs='a.txt')
file_set('rule_input',
    srcs=':file_input')
file_set('mixed_input',
    srcs=['b.txt', ':file_input'])
file_set('missing_input',
    srcs=':x')

file_set('multi_exts',
    srcs=['a.txt-a', 'b.txt-b', 'c.txt-c'])
file_set('only_a',
    srcs=':multi_exts',
    src_filter='*.txt-a')
file_set('only_ab',
    srcs=':multi_exts',
    src_filter='*.txt-a|*.txt-b')
