foo#*.ext for src_filter on input side
  removes extra intermediate rules (*.css only from set)

Caching
==============================================================

copy_files/etc need to preserve times

Stages
==============================================================

Commands emit a list of stages. Each stage is executed in order and only if the previous stage was skipped/succeeded.

StageManager:
  log_sinks
  log
  stages
  execute()

Stage:
  name
  log
  execute()

Simple commands can setup a single StageManager with stages and execute. The daemon would setup a new StageManager each time it goes to perform its work.

StageManagers setup LogSinks as needed (ConsoleLogSink, RemoteLogSink, FileLogSink) and wire up all the loggers.

Stages are logical subcommands, such as 'build', 'test', 'deploy', 'clean', etc. A 'rebuild' command may consist of 'clean' and 'build', where a 'test' command would have 'build' and 'test'.

Logging
==============================================================

LogSource
--------------------

Builds a line list of output from a single rule. Pickleable to allow for passing across processes.

* Name
* Parent / children
* Sinks
* Default verbosity level (inherit/+/-)
* Methods for debug/info/warn/error
* Status: waiting|running|succeeded|failed|skipped
* Exception
* start_time / end_time
* work_unit / work_unit_count for progress tracking

LogSink
-----------

Receives change notifications for all logger objects. For every field updated on a LogSource, the LogSink will get notified that the change occurred.

* source_open(source)
* source_set_status(source, value)
* source_set_exeception(source, ex)
* source_append_line(source, line)
* source_set_time(source, start_time, end_time)
* source_set_work_unit(source, work_unit, work_unit_count)
* source_close(source)

Example sinks:
* ConsoleLogSink: log to an interactive console
* FileLogSink: log simple output to a file/pipe
* RemoteLogSink: post to a log server

Flow
----

One ScopedLogger for the entire command, one for each stage (build/test/etc), and one for each rule.

Log Server
==============================================================

Starts a streaming log server that can be viewed in the browser to watch build status/test reports, as well as providing an API for build sessions to post data with.

anvil log_server --http_port=8000

* / : index
  * Report history
  * Live-updating 'in-progress' list
  * Basic machine stats (CPU %, etc)
* GET /report/N/ : report view
  * Info: build config/command line/etc
  * Timing information for whole report
  * Graph w/ timing for each node
    * State (success, fail, running, skipped)
    * Time elapsed
    * Click to show output
  * Console log (all output)
  * Test results
    * Take output from Buster/etc?
* POST /report/ : create report
* POST /report/N/ : update report

POST blobs
----------

Creation:
'''
{
  'host': {
    'name': 'some-machine',
    'platform': 'windows',
    'processors': 9,
    ...
  },
  'working_dir': '/some/path/',
  'command_line': 'anvil build --foo ...',
  'command': 'build',
  'stages': ['build', 'test', 'deploy'],
  'configuration': '...',
  'targets': [':c'],
  'graph': {
    'nodes': [
      {
        'name': ':a',
        'path': '/some/path:a',
        ...
      }
    ],
    'edges': [[':a', ':b'], [':b', ':c']]
  },
}
'''

Update:
'''
scoped logger blob:
// any fields can be omitted to not update that field
// output is always appended if present
'status': 'waiting|running|succeeded|failed|skipped',
'start_time': 0,
'end_time': 0,
'exception': undefined,
'output': 'new output',
'work_unit_count': 100,
'work_unit': 28,

{
  {scoped logger blob},

  'children': {
    'build': {
      {scoped logger blob},
      'children': {
        '/some/path:a': {
          {scoped logger blob},
          'src_paths': ['a', 'b'],
          'all_output_files': ['ax', 'bx']
        }
      }
    },
    'test': {
      {scoped logger blob},
      // something
    }
  }
}
'''


Serving/Daemon
==============================================================


anvilrc
==============================================================

Universal arg: '--anvil_config=...'
If not specified, search up cwd path until .anvilrc or .git/ found

Format
------

[core]
jobs=2
[commands]
search_paths=
    some/path/
[rules]
search_paths=
    some/path/
[serving]
http_port=8080
daemon_port=8081
[logging]
http_port=8000
...
