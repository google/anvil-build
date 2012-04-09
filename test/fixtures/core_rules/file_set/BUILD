file_set('a', srcs='a.txt')
file_set('a_glob', srcs=glob('*.txt'))

file_set('b_ref', srcs='dir:b')

file_set('all_glob', srcs=glob('**/*.txt'))

file_set('combo', srcs=[':a', ':b_ref'])
file_set('dupes', srcs=[':a', 'a.txt', ':b_ref', 'dir:b', ':combo'])
