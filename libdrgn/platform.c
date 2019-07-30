// Copyright 2019 - Omar Sandoval
// SPDX-License-Identifier: GPL-3.0+

#include <string.h>

#include "internal.h"
#include "platform.h"

static const struct drgn_architecture_info arch_info_unknown = {
	.name = "unknown",
	.arch = DRGN_ARCH_UNKNOWN,
};

LIBDRGN_PUBLIC const struct drgn_platform drgn_host_platform = {
#ifdef __x86_64__
	.arch = &arch_info_x86_64,
#else
	.arch = &arch_info_unknown,
#endif
	.flags = ((sizeof(void *) == 8 ? DRGN_PLATFORM_IS_64_BIT : 0) |
		  (__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__ ?
		   DRGN_PLATFORM_IS_LITTLE_ENDIAN : 0)),
};

LIBDRGN_PUBLIC struct drgn_error *
drgn_platform_create(enum drgn_architecture arch,
		     enum drgn_platform_flags flags, struct drgn_platform **ret)
{
	const struct drgn_architecture_info *arch_info;
	struct drgn_platform *platform;

	switch (arch) {
	case DRGN_ARCH_UNKNOWN:
		arch_info = &arch_info_unknown;
		break;
	case DRGN_ARCH_X86_64:
		arch_info = &arch_info_x86_64;
		break;
	default:
		return drgn_error_create(DRGN_ERROR_INVALID_ARGUMENT,
					 "invalid architecture");
	}
	if (flags == DRGN_PLATFORM_DEFAULT_FLAGS) {
		if (arch == DRGN_ARCH_UNKNOWN) {
			return drgn_error_create(DRGN_ERROR_INVALID_ARGUMENT,
						 "cannot get default platform flags of unknown architecture");
		}
		flags = arch_info->default_flags;
	} else if (flags & ~DRGN_ALL_PLATFORM_FLAGS) {
		return drgn_error_create(DRGN_ERROR_INVALID_ARGUMENT,
					 "invalid platform flags");
	}
	platform = malloc(sizeof(*platform));
	if (!platform)
		return &drgn_enomem;
	platform->arch = arch_info;
	platform->flags = flags;
	*ret = platform;
	return NULL;
}

LIBDRGN_PUBLIC void drgn_platform_destroy(struct drgn_platform *platform)
{
	free(platform);
}

LIBDRGN_PUBLIC enum drgn_architecture
drgn_platform_arch(const struct drgn_platform *platform)
{
	return platform->arch->arch;
}

LIBDRGN_PUBLIC enum drgn_platform_flags
drgn_platform_flags(const struct drgn_platform *platform)
{
	return platform->flags;
}

LIBDRGN_PUBLIC bool drgn_platform_eq(struct drgn_platform *a,
				     struct drgn_platform *b)
{
	return a->arch == b->arch && a->flags == b->flags;
}

void drgn_platform_from_elf(GElf_Ehdr *ehdr, struct drgn_platform *ret)
{
	switch (ehdr->e_machine) {
	case EM_X86_64:
		ret->arch = &arch_info_x86_64;
		ret->flags = DRGN_PLATFORM_IS_LITTLE_ENDIAN;
		if (ehdr->e_ident[EI_CLASS] == ELFCLASS64)
			ret->flags |= DRGN_PLATFORM_IS_64_BIT;
		break;
	default:
		/*
		 * For architectures that we don't recognize, we assume that the
		 * word size and endianness match that of the ELF file.
		 */
		ret->arch = &arch_info_unknown;
		ret->flags = 0;
		if (ehdr->e_ident[EI_CLASS] == ELFCLASS64)
			ret->flags |= DRGN_PLATFORM_IS_64_BIT;
		if (ehdr->e_ident[EI_DATA] == ELFDATA2LSB)
			ret->flags |= DRGN_PLATFORM_IS_LITTLE_ENDIAN;
		break;
	}
}
