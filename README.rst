drgn
====

.. image:: https://travis-ci.org/osandov/drgn.svg?branch=master
    :target: https://travis-ci.org/osandov/drgn
    :alt: Build Status

.. image:: https://readthedocs.org/projects/drgn/badge/?version=latest
    :target: https://drgn.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. start-introduction

drgn (pronounced "dragon") is a debugger-as-a-library. In contrast to existing
debuggers like `GDB <https://www.gnu.org/software/gdb/>`_ which focus on
breakpoint-based debugging, drgn excels in live introspection. drgn exposes the
types and variables in a program for easy, expressive scripting in Python. For
example, you can debug the Linux kernel:

.. code-block:: pycon

    >>> from drgn.helpers.linux import list_for_each_entry
    >>> for mod in list_for_each_entry('struct module',
    ...                                prog['modules'].address_of_(),
    ...                                'list'):
    ...    if mod.refcnt.counter > 10:
    ...        print(mod.name)
    ...
    (char [56])"snd"
    (char [56])"evdev"
    (char [56])"i915"

drgn was developed for debugging the Linux kernel (as an alternative to the
`crash <http://people.redhat.com/anderson/>`_ utility), but it can also debug
userspace programs written in C. C++ support is planned.

.. end-introduction

Documentation can be found at `drgn.readthedocs.io
<https://drgn.readthedocs.io>`_.

Installation
------------

.. start-install-dependencies

Install dependencies:

Arch Linux::

    $ sudo pacman -S --needed autoconf automake bison bzip2 flex gawk gcc libtool make pkgconf python python-setuptools xz zlib

Debian/Ubuntu::

    $ sudo apt-get install autoconf automake bison flex gawk gcc libbz2-dev liblzma-dev libtool make pkgconf python3 python3-dev python3-setuptools zlib1g-dev

Note that Debian Stretch, Ubuntu Trusty, and Ubuntu Xenial (and older) ship
Python versions which are too old. Python 3.6 or newer must be installed
manually.

Fedora::

    $ sudo dnf install autoconf automake bison bzip2-devel flex gawk gcc libtool make pkgconf python3 python3-devel python3-setuptools xz-devel zlib-devel

Optionally, install:

* `libkdumpfile <https://github.com/ptesarik/libkdumpfile>`_ if you want
  support for kdump-compressed kernel core dumps

.. end-install-dependencies

Then, run:

.. code-block:: console

    $ git clone https://github.com/osandov/drgn.git
    $ cd drgn
    $ python3 setup.py build
    $ sudo python3 setup.py install

See the `installation documentation
<https://drgn.readthedocs.io/en/latest/installation.html>`_ for more details.

Quick Start
-----------

.. start-quick-start

drgn debugs the running kernel by default; run ``sudo drgn``. To debug a
running program, run ``sudo drgn -p $PID``. To debug a core dump (either a
kernel vmcore or a userspace core dump), run ``drgn -c $PATH``. The program
must have debugging symbols available.

Then, you can access variables in the program with ``prog['name']``, access
structure members with ``.``, use various predefined helpers, and more:

.. code-block:: pycon

    $ sudo drgn
    >>> prog['init_task'].comm
    (char [16])"swapper/0"
    >>> d_path(fget(find_task(prog, 1), 0).f_path.address_of_())
    b'/dev/null'
    >>> max(task.stime for task in for_each_task(prog))
    (u64)4192109975952
    >>> sum(disk.gendisk.part0.nr_sects for disk in for_each_disk(prog))
    (sector_t)999705952

.. end-quick-start

See the `user guide <https://drgn.readthedocs.io/en/latest/user_guide.html>`_
for more information.

License
-------

.. start-license

Copyright 2018-2019 Omar Sandoval

drgn is licensed under the `GPLv3
<https://www.gnu.org/licenses/gpl-3.0.en.html>`_ or later.

.. end-license
