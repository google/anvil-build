file_set('b', srcs='b.txt')
template_files(
    name='template_b',
    srcs='b.txt',
    params={'hello': 'world_b',})
template_files(
    name='template_b_rule',
    srcs=':b',
    params={'hello': 'world_b_rule',})
