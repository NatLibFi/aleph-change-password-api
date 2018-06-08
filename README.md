# HTTP API to change user password in Aleph
## installation
1. Create CGI script that should be called by the HTTP server:
```sh
#!/bin/bash
export LD_LIBRARY_PATH=<path-to-oracle-instantclient>
export CONFIGURATION_FILE=<path-to-app-config>
/opt/csw/bin/python2.7 <path-to-change-aleph-user-password-cgi>
```
1. Give execute permissions to $aleph_proc/proc/p_file_06

## License and copyright

Copyright (c) 2017-2018 **University Of Helsinki (The National Library Of Finland)**

This project's source code is licensed under the terms of **Apache License 2.0**.
