# The `multibeton_modbus` subpackage

`custom_components/multibeton/multibeton_modbus/` is the register-level
Modbus layer of this integration: typed field descriptors for the
controller's registers, grouped into subsystems, with no dependency on Home
Assistant. It is ordinary source code of this project and is maintained
here.

## Dependencies

The layer is written against
[`modbus-connection`](https://pypi.org/project/modbus-connection/), the only
entry in `manifest.json`'s `requirements`, pinned `>=4.8.1,<5`. The
integration drives its `tmodbus` backend, requested through the
`modbus-connection[tmodbus]` extra; Home Assistant installs both
automatically.

## Licensing

Copyright MULTIBETON GmbH. Like the rest of the repository, the subpackage is
released under the MIT license in the repository root's `LICENSE`.
