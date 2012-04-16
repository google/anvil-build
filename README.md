Anvil - a modern build system
-----------------------------

[![Build Status](https://secure.travis-ci.org/benvanik/anvil-build.png)](http://travis-ci.org/benvanik/anvil-build)

Anvil is a build system designed to ease the construction of content pipelines, taking many concepts and the rule file syntax that powers Google's internal build system and making them accessible in a small, open-source Python library. It features a rich and extensible build file format and many built-in rules to get started.

Modern web apps and games have shifted to be more content than code and older build systems (make/scons/etc) are ill-suited for this shift. Most developers now roll their own shell scripts and hack together tools, but as projects scale in both size and complexity they fall apart. Limiting the engineering robustness of many large games is now this lack of solid content pipeline, not language or browser features. Anvil is designed to help fill this gap and let developers build polished, efficient, and cross-browser applications.

Features
--------

* Parallelizable build process
 * Eventually distributed
* Rich build files (Python-like)
* Tiny environment, very few assumptions or dependencies
 * Build files are generally WYSIWYG, with no hidden state or behavior
* Continuous build server and hosting mode
 * Easy to build live-refresh pages and content
* Dependency management for rule types
 * Make it simple to checkout and build projects that depend on custom tools or packages
* Extensible rule definitions
 * Simple Python to add custom data formats or actions

Getting Started
---------------
  
    # Clone (or add as a submodule) and setup a local install
    git clone https://benvanik@github.com/benvanik/anvil-build.git
    cd anvil-build/
    python setup.py develop
    
    # 'anvil' is the main app, use it to build, test, or serve your content
    anvil build project:some_output
  
Anvil is available via PyPI as '[anvil-build](http://pypi.python.org/pypi/anvil-build)' and can be installed via easy_install or pip, however it's recommeneded that it's used as a submodule instead.

    # Install the master git dev branch
    pip install anvil-build
    
Note that bash completion should be enable, but if not use `sudo anvil completion --install --bash` to install it. You can complete on options, module files, and if you add a `:` on rules.
  
Build Files
-----------

TODO: detailed overview

The base unit in the build system is a rule. Rules describe some action that is performed on input files and produce output files, and they may reference other rules as inputs. Modules are files that contain many rules, and a project may be made up of many modules. When using the 'anvil' command line tool one specifies a rule or list of rules to build as targets and the build system takes care of building all of the required rules.

The naming syntax for rules is `/some/path:rule_name`, with the colon splitting module file paths from the rule names contained within. The module files should always be called `BUILD`, which is a special name that the build system treats as the module for the parent directory. This enables one to omit `BUILD` when referencing rules, auto-expanding `/some/path:rule_name` to `/some/path/BUILD:rule_name`. A shorthand is allowed as `:rule_name` (omitting the path), enabling easy access to rules defined in the same file or, when dealing with rules from the command line, in the BUILD file in the current working directory.

For example, here's two simple files:

    # in /some/path/BUILD:
    # All txt files under the current path, plus the outputs of foo:rule2
    file_set(name='rule1', srcs=glob('**/*.txt') + ['foo:rule2'])
    
    # in /some/path/foo/BUILD:
    file_set(name='rule2', srcs=['some_file.js'])
    
From the command line when referencing these files:

    # if cwd = /some/path, all of these are equivalent:
    anvil build :rule1
    anvil build /some/path:rule1
    anvil build /some/path/BUILD:rule1
    
TODO: dumping the build graph
    
Rules
-----

All rules have a few shared parameters, and most use them exclusively to do their work:

* `name`: The name of the rule when referenced. Some rules will use this as the base name of their output file.
* `srcs`: A list of source files the rule works on. May reference files, globs, or other rules.
* `deps`: A list of rules that must execute before the rule does, but the files are not used.

TODO: talk about base rules (`file_set`, `copy_files`, `concat_files`, `template_files`)

Commands
--------

TODO: talk about built-in commands (`build`, `test`, `clean`, `depends`, `deploy`, `serve`)

Custom Rules
------------

TODO: custom rules/.anvilrc files
