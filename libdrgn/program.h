// Copyright 2018-2019 - Omar Sandoval
// SPDX-License-Identifier: GPL-3.0+

/**
 * @file
 *
 * Program internals.
 *
 * See @ref ProgramInternals.
 */

#ifndef DRGN_PROGRAM_H
#define DRGN_PROGRAM_H

#include <elfutils/libdwfl.h>
#ifdef WITH_LIBKDUMPFILE
#include <libkdumpfile/kdumpfile.h>
#endif

#include "memory_reader.h"
#include "object_index.h"
#include "platform.h"
#include "type_index.h"

/**
 * @ingroup Internals
 *
 * @defgroup ProgramInternals Programs
 *
 * Program internals.
 *
 * @{
 */

/** The important parts of the VMCOREINFO note of a Linux kernel core. */
struct vmcoreinfo {
	/** <tt>uname -r</tt> */
	char osrelease[128];
	/** PAGE_SIZE of the kernel. */
	uint64_t page_size;
	/**
	 * The offset from the compiled address of the kernel image to its
	 * actual address in memory.
	 *
	 * This is non-zero if kernel address space layout randomization (KASLR)
	 * is enabled.
	 */
	uint64_t kaslr_offset;
};

struct drgn_dwarf_info_cache;
struct drgn_dwarf_index;

struct drgn_program {
	/** @privatesection */
	struct drgn_memory_reader reader;
	struct drgn_type_index tindex;
	struct drgn_object_index oindex;
	struct drgn_memory_file_segment *file_segments;
	size_t num_file_segments;
	/*
	 * Valid iff <tt>flags & DRGN_PROGRAM_IS_LINUX_KERNEL</tt>.
	 */
	struct vmcoreinfo vmcoreinfo;
	 /*
	  * Valid iff
	  * <tt>(flags & (DRGN_PROGRAM_IS_LINUX_KERNEL | DRGN_PROGRAM_IS_LIVE)) ==
	  * DRGN_PROGRAM_IS_LIVE</tt>.
	  */
	pid_t pid;
#ifdef WITH_LIBKDUMPFILE
	kdump_ctx_t *kdump_ctx;
#endif
	struct drgn_dwarf_info_cache *_dicache;
	/* See @ref drgn_object_stack_trace_next_thread(). */
	const struct drgn_object *stack_trace_obj;
	/* See @ref drgn_object_stack_trace(). */
	struct drgn_error *stack_trace_err;
	int core_fd;
	enum drgn_program_flags flags;
	struct drgn_platform platform;
	bool has_platform;
	bool added_vmcoreinfo_object_finder;
	bool attached_dwfl_state;
};

/** Initialize a @ref drgn_program. */
void drgn_program_init(struct drgn_program *prog,
		       const struct drgn_platform *platform);

/** Deinitialize a @ref drgn_program. */
void drgn_program_deinit(struct drgn_program *prog);

/**
 * Set the @ref drgn_platform of a @ref drgn_program if it hasn't been set
 * yet.
 */
void drgn_program_set_platform(struct drgn_program *prog,
			       const struct drgn_platform *platform);

/**
 * Implement @ref drgn_program_from_core_dump() on an initialized @ref
 * drgn_program.
 */
struct drgn_error *drgn_program_init_core_dump(struct drgn_program *prog,
					       const char *path);

/**
 * Implement @ref drgn_program_from_kernel() on an initialized @ref
 * drgn_program.
 */
struct drgn_error *drgn_program_init_kernel(struct drgn_program *prog);

/**
 * Implement @ref drgn_program_from_pid() on an initialized @ref drgn_program.
 */
struct drgn_error *drgn_program_init_pid(struct drgn_program *prog, pid_t pid);

static inline bool drgn_program_is_little_endian(struct drgn_program *prog)
{
	assert(prog->has_platform);
	return prog->platform.flags & DRGN_PLATFORM_IS_LITTLE_ENDIAN;
}

static inline bool drgn_program_is_64_bit(struct drgn_program *prog)
{
	assert(prog->has_platform);
	return prog->platform.flags & DRGN_PLATFORM_IS_64_BIT;
}

struct drgn_error *drgn_program_get_dwfl(struct drgn_program *prog, Dwfl **ret);

/*
 * Like @ref drgn_program_find_symbol(), but @p ret is already allocated and
 * returns @ref drgn_not_found instead of a more informative message.
 */
struct drgn_error *drgn_program_find_symbol_internal(struct drgn_program *prog,
						     uint64_t address,
						     struct drgn_symbol *ret);

/** @} */

#endif /* DRGN_PROGRAM_H */
