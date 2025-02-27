# gbp-archive

A Gentoo Build Publisher plugin to dump & restore builds.

# Description

The `gbp-archive` package provides two subcommands for gbpcli: `dump` and
`restore`. These subcommands are "server-only" meaning they are only available
from the GBP server instance.  The `dump` subcommand can dump all the builds
on the instance, just a particular machine or machines, or a particular build
or builds, or any combination of those.

![screenshot](https://raw.githubusercontent.com/enku/screenshots/refs/heads/master/gbp-archive/dump-usage.svg)

Then restoring is as simple as running `gbp restore`:

![screenshot](https://raw.githubusercontent.com/enku/screenshots/refs/heads/master/gbp-archive/restore-usage.svg)

# Process

## Dump

How the dump process works is a tar archive is created. Inside that tar
archive are 3 items:

### Metadata

The first item is a JSON file containing metadata for the dump. Currently the
metadata are:

- The version number of the dump file
- A timestamp for when the dump was created
- The hostname of the GBP instance that created the dump
- The list of builds included in the dump

### Records

The second item is a file which includes all the "records" for the dumped
builds.  This is the build metadata stored the GBP database. This information
is serialized into JSON and stored in a single file, `records.json`.

### Storage

The third item is another tar archive consisting of the "storage" for the
dumped builds. By storage I mean all of the repos, binpkgs, and configuration
for builds.  All of them are stored in an inner tar archive called
`storage.tar`. The reason for the single archive and not one archive per build
is to preserve the multiple hard links which span across builds (for a given
machine). They would not be preserved across multiple archives.


## Restore

For the restore process, we open the outer tar archive and then the
`records.json` file is deserialized and loaded into the instance's database.
Then we extract the contents of `storage.tar` to the root of the instance's
storage root.  Currently the restore process is all-or-nothing. But in the
future I will add the ability to filter out what builds get restored.
