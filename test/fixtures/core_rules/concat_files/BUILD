concat_files(
    name='concat',
    srcs=['1.txt', '2.txt', '3.txt', '4.txt'])

concat_files(
    name='concat_out',
    srcs=['1.txt', '2.txt', '3.txt', '4.txt'],
    out='concat.txt')

concat_files(
    name='concat_template',
    srcs=[':concat_out', 't.txt', ':concat_out'])
template_files(
    name='templated',
    srcs=[':concat_template',],
    new_extension='.out',
    params={'hello': 'world!'})
