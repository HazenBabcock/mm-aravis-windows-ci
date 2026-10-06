# License overrides

`scripts/arrange_3rdpartypublic.py` copies each package's license from vcpkg
into the `licenses` directory of the arranged files. For a package listed
here, it uses the file in this directory instead, because the one vcpkg
installs is not the license text itself.

- `pcre2.txt`: `LICENCE.md` from PCRE2 10.47 (tag `pcre2-10.47` of
  [PCRE2Project/pcre2](https://github.com/PCRE2Project/pcre2)). vcpkg installs
  PCRE2's `COPYING`, which only says to see `LICENCE` in the PCRE2
  distribution.

Update a file here when vcpkg moves the package to a new version.
