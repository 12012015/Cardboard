pkgdatadir = get_option('prefix') / get_option('datadir')

application_id = 'io.github._12012015.Cardboard'
name = meson.project_name()

gnome = import('gnome')

gnome.compile_resources(name,
    name + '.gresource.xml',
    gresource_bundle: true,
    install: true,
    install_dir: pkgdatadir / meson.project_name(),
)

desktop_file = i18n.merge_file(
    input: application_id + '.desktop.in',
    output: application_id + '.desktop',
    type: 'desktop',
    po_dir: '../po',
    install: true,
    install_dir: pkgdatadir / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

appstream_file = i18n.merge_file(
    input: application_id + '.metainfo.xml.in',
    output: application_id + '.metainfo.xml',
    po_dir: '../po',
    install: true,
    install_dir: pkgdatadir / 'metainfo'
)

appstreamcli = find_program('appstreamcli', required: false, disabler: true)
test('Validate appstream file', appstreamcli,
    args: ['validate', '--no-net', '--explain', appstream_file])

install_data(application_id + '.gschema.xml',
    install_dir: pkgdatadir / 'glib-2.0' / 'schemas'
)

compile_schemas = find_program('glib-compile-schemas', required: true)
test('Validate schema file',
     compile_schemas,
     args: ['--strict', '--dry-run', meson.current_source_dir()])

scalable_dir = 'hicolor' / 'scalable' / 'apps'
symbolic_dir = 'hicolor' / 'symbolic' / 'apps'

install_data(
    'icons' / (application_id + '.svg'),
    install_dir: pkgdatadir / 'icons' / scalable_dir
)

install_data(
    'icons' / (application_id + '-symbolic.svg'),
    install_dir: pkgdatadir / 'icons' / symbolic_dir
)