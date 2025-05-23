pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('pkgdatadir', pkgdatadir)

configure_file(
    input: meson.project_name() + '.in',
    output: meson.project_name(),
    configuration: conf,
    install: true,
    install_dir: get_option('bindir'),
    install_mode: 'r-xr-xr-x'
)

sources = [
    'py/main.py',
    'py/preferences.py',
    'py/tab.py',
    'py/danbooru.py',
    'py/post.py'
]

install_data(sources, install_dir: pkgdatadir / meson.project_name())