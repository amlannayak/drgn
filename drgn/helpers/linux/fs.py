# Copyright 2018-2019 - Omar Sandoval
# SPDX-License-Identifier: GPL-3.0+

"""
Virtual Filesystem Layer
------------------------

The ``drgn.helpers.linux.fs`` module provides helpers for working with the
Linux virtual filesystem (VFS) layer, including mounts, dentries, and inodes.
"""

import os

from drgn import Object, Program, container_of
from drgn.helpers import escape_string
from drgn.helpers.linux.list import (
    hlist_empty,
    hlist_for_each_entry,
    list_for_each_entry,
    list_for_each_entry_reverse,
)

__all__ = [
    'path_lookup',
    'd_path',
    'dentry_path',
    'inode_path',
    'inode_paths',
    'mount_src',
    'mount_dst',
    'mount_fstype',
    'for_each_mount',
    'print_mounts',
    'fget',
    'for_each_file',
    'print_files',
]


def _follow_mount(mnt, dentry):
    # DCACHE_MOUNTED is a macro, so we can't easily get the value. But, it
    # hasn't changed since v2.6.38, so let's hardcode it for now.
    DCACHE_MOUNTED = 0x10000
    while dentry.d_flags & DCACHE_MOUNTED:
        for other_mnt in list_for_each_entry_reverse('struct mount',
                                                     mnt.mnt_ns.list.address_of_(),
                                                     'mnt_list'):
            if other_mnt.mnt_mountpoint == dentry:
                mnt = other_mnt.read_()
                dentry = mnt.mnt.mnt_root.read_()
                break
        else:
            break
    return mnt, dentry


def _follow_dotdot(mnt, dentry, root_mnt, root_dentry):
    while dentry != root_dentry or mnt != root_mnt:
        d_parent = dentry.d_parent.read_()
        if dentry != d_parent:
            dentry = d_parent
            break
        mnt_parent = mnt.mnt_parent.read_()
        if mnt == mnt_parent:
            break
        dentry = mnt.mnt_mountpoint
        mnt = mnt_parent
    return _follow_mount(mnt, dentry)


def path_lookup(prog_or_root, path, allow_negative=False):
    """
    .. c:function:: struct path path_lookup(struct path *root, const char *path, bool allow_negative)

    Look up the given path name relative to the given root directory. If given
    a :class:`Program` instead of a ``struct path``, the initial root
    filesystem is used.

    :param bool allow_negative: Whether to allow returning a negative dentry
        (i.e., a dentry for a non-existent path).
    :raises Exception: if the dentry is negative and ``allow_negative`` is
        ``False``, or if the path is not present in the dcache. The latter does
        not necessarily mean that the path does not exist; it may be uncached.
        On a live system, you can make the kernel cache the path by accessing
        it (e.g., with :func:`open()` or :func:`os.stat()`):

        >>> path_lookup(prog, '/usr/include/stdlib.h')
        ...
        Exception: could not find '/usr/include/stdlib.h' in dcache
        >>> open('/usr/include/stdlib.h').close()
        >>> path_lookup(prog, '/usr/include/stdlib.h')
        (struct path){
                .mnt = (struct vfsmount *)0xffff8b70413cdca0,
                .dentry = (struct dentry *)0xffff8b702ac2c480,
        }
    """
    if isinstance(prog_or_root, Program):
        prog_or_root = prog_or_root['init_task'].fs.root
    mnt = root_mnt = container_of(prog_or_root.mnt.read_(), 'struct mount',
                                  'mnt')
    dentry = root_dentry = prog_or_root.dentry.read_()
    components = os.fsencode(path).split(b'/')
    for i, component in enumerate(components):
        if component == b'' or component == b'.':
            continue
        elif component == b'..':
            mnt, dentry = _follow_dotdot(mnt, dentry, root_mnt, root_dentry)
        else:
            for child in list_for_each_entry('struct dentry',
                                             dentry.d_subdirs.address_of_(),
                                             'd_child'):
                if child.d_name.name.string_() == component:
                    dentry = child
                    break
            else:
                failed_path = os.fsdecode(b'/'.join(components[:i + 1]))
                raise Exception(f'could not find {failed_path!r} in dcache')
            mnt, dentry = _follow_mount(mnt, dentry)
    if not allow_negative and not dentry.d_inode:
        failed_path = os.fsdecode(b'/'.join(components))
        raise Exception(f'{failed_path!r} dentry is negative')
    return Object(mnt.prog_, 'struct path', value={
        'mnt': mnt.mnt.address_of_(),
        'dentry': dentry,
    })


def d_path(path_or_vfsmnt, dentry=None):
    """
    .. c:function:: char *d_path(struct path *path)
    .. c:function:: char *d_path(struct vfsmount *vfsmnt, struct dentry *dentry)

    Return the full path of a dentry given a ``struct path *`` or a mount and a
    dentry.
    """
    type_name = str(path_or_vfsmnt.type_.type_name())
    if type_name == 'struct path' or type_name == 'struct path *':
        vfsmnt = path_or_vfsmnt.mnt
        dentry = path_or_vfsmnt.dentry.read_()
    else:
        vfsmnt = path_or_vfsmnt
        dentry = dentry.read_()
    mnt = container_of(vfsmnt, 'struct mount', 'mnt')

    d_op = dentry.d_op.read_()
    if d_op and d_op.d_dname:
        return None

    components = []
    while True:
        while True:
            d_parent = dentry.d_parent.read_()
            if dentry == d_parent:
                break
            components.append(dentry.d_name.name.string_())
            components.append(b'/')
            dentry = d_parent
        mnt_parent = mnt.mnt_parent.read_()
        if mnt == mnt_parent:
            break
        dentry = mnt.mnt_mountpoint
        mnt = mnt_parent
    if components:
        return b''.join(reversed(components))
    else:
        return b'/'


def dentry_path(dentry):
    """
    .. c:function:: char *dentry_path(struct dentry *dentry)

    Return the path of a dentry from the root of its filesystem.
    """
    components = []
    while True:
        d_parent = dentry.d_parent.read_()
        if dentry == d_parent:
            break
        components.append(dentry.d_name.name.string_())
        dentry = d_parent
    return b'/'.join(reversed(components))


def inode_path(inode):
    """
    .. c:function:: char *inode_path(struct inode *inode)

    Return any path of an inode from the root of its filesystem.
    """
    if hlist_empty(inode.i_dentry):
        return None
    return dentry_path(container_of(inode.i_dentry.first, 'struct dentry',
                                    'd_u.d_alias'))


def inode_paths(inode):
    """
    .. c:function:: inode_paths(struct inode *inode)

    Return an iterator over all of the paths of an inode from the root of its
    filesystem.

    :rtype: Iterator[bytes]
    """
    return (
        dentry_path(dentry) for dentry in
        hlist_for_each_entry('struct dentry', inode.i_dentry.address_of_(),
                             'd_u.d_alias')
    )


def mount_src(mnt):
    """
    .. c:function:: char *mount_src(struct mount *mnt)

    Get the source device name for a mount.

    :rtype: bytes
    """
    return mnt.mnt_devname.string_()


def mount_dst(mnt):
    """
    .. c:function:: char *mount_dst(struct mount *mnt)

    Get the path of a mount point.

    :rtype: bytes
    """
    return d_path(mnt.mnt.address_of_(), mnt.mnt.mnt_root)


def mount_fstype(mnt):
    """
    .. c:function:: char *mount_fstype(struct mount *mnt)

    Get the filesystem type of a mount.

    :rtype: bytes
    """
    sb = mnt.mnt.mnt_sb.read_()
    fstype = sb.s_type.name.string_()
    subtype = sb.s_subtype.read_()
    if subtype:
        subtype = subtype.string_()
        if subtype:
            fstype += b'.' + subtype
    return fstype


def for_each_mount(prog_or_ns, src=None, dst=None, fstype=None):
    """
    .. c:function:: for_each_mount(struct mnt_namespace *ns, char *src, char *dst, char *fstype)

    Iterate over all of the mounts in a given namespace. If given a
    :class:`Program` instead, the initial mount namespace is used. returned
    mounts can be filtered by source, destination, or filesystem type, all of
    which are encoded using :func:`os.fsencode()`.

    :return: Iterator of ``struct mount *`` objects.
    """
    if isinstance(prog_or_ns, Program):
        ns = prog_or_ns['init_task'].nsproxy.mnt_ns
    else:
        ns = prog_or_ns
    if src is not None:
        src = os.fsencode(src)
    if dst is not None:
        dst = os.fsencode(dst)
    if fstype:
        fstype = os.fsencode(fstype)
    for mnt in list_for_each_entry('struct mount', ns.list.address_of_(),
                                   'mnt_list'):
        if ((src is None or mount_src(mnt) == src) and
                (dst is None or mount_dst(mnt) == dst) and
                (fstype is None or mount_fstype(mnt) == fstype)):
            yield mnt


def print_mounts(prog_or_ns, src=None, dst=None, fstype=None):
    """
    .. c:function:: print_mounts(struct mnt_namespace *ns, char *src, char *dst, char *fstype)

    Print the mount table of a given namespace. The arguments are the same as
    :func:`for_each_mount()`. The output format is similar to ``/proc/mounts``
    but prints the value of each ``struct mount *``.
    """
    for mnt in for_each_mount(prog_or_ns, src, dst, fstype):
        mnt_src = escape_string(mount_src(mnt), escape_backslash=True)
        mnt_dst = escape_string(mount_dst(mnt), escape_backslash=True)
        mnt_fstype = escape_string(mount_fstype(mnt), escape_backslash=True)
        print(f'{mnt_src} {mnt_dst} {mnt_fstype} ({mnt.type_.type_name()})0x{mnt.value_():x}')


def fget(task, fd):
    """
    .. c:function:: struct file *fget(struct task_struct *task, int fd)

    Return the kernel file descriptor of the fd of a given task.
    """
    return task.files.fdt.fd[fd]


def for_each_file(task):
    """
    .. c:function:: for_each_file(struct task_struct *task)

    Iterate over all of the files open in a given task.

    :return: Iterator of (fd, ``struct file *``) tuples.
    :rtype: Iterator[tuple[int, Object]]
    """
    fdt = task.files.fdt.read_()
    bits_per_long = 8 * fdt.open_fds.type_.type.size
    for i in range((fdt.max_fds.value_() + bits_per_long - 1) // bits_per_long):
        word = fdt.open_fds[i].value_()
        for j in range(bits_per_long):
            if word & (1 << j):
                fd = i * bits_per_long + j
                file = fdt.fd[fd].read_()
                yield fd, file


def print_files(task):
    """
    .. c:function:: print_files(struct task_struct *task)

    Print the open files of a given task.
    """
    for fd, file in for_each_file(task):
        path = d_path(file.f_path)
        if path is None:
            path = file.f_inode.i_sb.s_type.name.string_()
        path = escape_string(path, escape_backslash=True)
        print(f'{fd} {path} ({file.type_.type_name()})0x{file.value_():x}')
