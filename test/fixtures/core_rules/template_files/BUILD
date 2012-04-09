file_set('a', srcs='a.txt')
template_files(
    name='template_a',
    srcs='a.txt',
    params={'hello': 'world_a',})
template_files(
    name='template_a_rule',
    srcs=':a',
    params={'hello': 'world_a_rule',})

file_set('all_glob', srcs=glob('**/*.txt'))
template_files(
    name='template_all',
    srcs=':all_glob',
    params={'hello': 'world',})

template_files(
    name='template_dep_1',
    srcs=glob('**/*.nfo'),
    params={'arg1': '${arg2}',})
template_files(
    name='template_dep_2',
    srcs=':template_dep_1',
    new_extension='.out',
    params={'arg2': 'world!',})
