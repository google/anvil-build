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

file_set('file_input',
    srcs='a.txt')
file_set('rule_input',
    srcs=':file_input')
file_set('mixed_input',
    srcs=['b.txt', ':file_input'])
file_set('missing_input',
    srcs=':x')
