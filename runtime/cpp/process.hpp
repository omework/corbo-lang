// SPDX-License-Identifier: MIT OR Apache-2.0
#ifndef CORBO_CPP_PROCESS_HPP
#define CORBO_CPP_PROCESS_HPP
struct corbo_argument_list { corbo_text *data; size_t len; unsigned status; };
inline corbo_argument_list corbo_arguments;
#if defined(_WIN32)
// Decode the documented Windows command-line quoting rules without shell APIs
// or CommandLineToArgvW's heap allocation. The caller provides fixed storage.
static inline bool corbo_windows_argument(const wchar_t *input, size_t length, size_t *position,
                                         uint8_t *output, size_t capacity, size_t *written) {
    bool quoted = false;
    size_t used = 0;
    while (*position < length && (quoted || (input[*position] != L' ' && input[*position] != L'\t'))) {
        size_t slashes = 0;
        while (*position < length && input[*position] == L'\\') { ++slashes; ++*position; }
        if (*position < length && input[*position] == L'"') {
            size_t escaped = slashes / 2;
            if (escaped > capacity - used) return false;
            while (escaped-- != 0) output[used++] = '\\';
            if (slashes % 2 != 0) { if (used == capacity) return false; output[used++] = '"'; ++*position; }
            else if (quoted && *position + 1 < length && input[*position + 1] == L'"') {
                if (used == capacity) return false; output[used++] = '"'; *position += 2;
            } else { quoted = !quoted; ++*position; }
            continue;
        }
        if (slashes > capacity - used) return false;
        while (slashes-- != 0) output[used++] = '\\';
        if (*position == length || (!quoted && (input[*position] == L' ' || input[*position] == L'\t'))) break;
        uint32_t scalar = (uint16_t)input[(*position)++];
        if (scalar >= 0xd800 && scalar <= 0xdbff) {
            if (*position == length) return false;
            uint32_t low = (uint16_t)input[(*position)++];
            if (low < 0xdc00 || low > 0xdfff) return false;
            scalar = 0x10000 + (scalar - 0xd800) * 1024 + low - 0xdc00;
        } else if (scalar >= 0xdc00 && scalar <= 0xdfff) return false;
        size_t width = scalar < 0x80 ? 1 : scalar < 0x800 ? 2 : scalar < 0x10000 ? 3 : 4;
        if (width > capacity - used) return false;
        if (width == 1) output[used++] = (uint8_t)scalar;
        else {
            if (width == 2) output[used++] = (uint8_t)(0xc0 | scalar >> 6);
            else if (width == 3) { output[used++] = (uint8_t)(0xe0 | scalar >> 12); output[used++] = (uint8_t)(0x80 | (scalar >> 6 & 63)); }
            else { output[used++] = (uint8_t)(0xf0 | scalar >> 18); output[used++] = (uint8_t)(0x80 | (scalar >> 12 & 63)); output[used++] = (uint8_t)(0x80 | (scalar >> 6 & 63)); }
            output[used++] = (uint8_t)(0x80 | (scalar & 63));
        }
    }
    *written = used;
    return true;
}
#endif
// Argument descriptors live below the root function's fixed-stack mark.
static inline void corbo_process_args_setup(int argc, char **argv) {
    corbo_arguments = {};
#if defined(_WIN32)
    const wchar_t *command = GetCommandLineW();
    if (command == NULL) { corbo_arguments.status = 2; return; }
    size_t length = 0; while (command[length] != 0) ++length;
    if (length > (SIZE_MAX - 1) / 4 || length + 1 > SIZE_MAX / sizeof(corbo_text)) {
        corbo_arguments.status = 2; return;
    }
    uint8_t *bytes = (uint8_t *)corbo_stack_alloc(length * 4 + 1, 1);
    corbo_text *arguments = (corbo_text *)corbo_stack_alloc((length + 1) * sizeof(corbo_text), alignof(corbo_text));
    size_t position = 0, used = 0, count = 0;
    // argv[0] has its own quoting convention and never belongs to env::args().
    if (length != 0 && command[0] != L' ' && command[0] != L'\t') {
        bool quoted = false;
        while (position < length) {
            wchar_t value = command[position];
            if (value == L'"') quoted = !quoted;
            else if (!quoted && (value == L' ' || value == L'\t')) break;
            ++position;
        }
    }
    while (position < length) {
        while (position < length && (command[position] == L' ' || command[position] == L'\t')) ++position;
        if (position == length) break;
        size_t written = 0;
        if (!corbo_windows_argument(command, length, &position, bytes + used, length * 4 + 1 - used, &written)) {
            corbo_arguments.status = 1; return;
        }
        // Leading whitespace denotes an empty executable argument, as the CRT does.
        ::new (&arguments[count++]) corbo_text{bytes + used, written};
        used += written;
    }
    corbo_arguments.data = arguments; corbo_arguments.len = count;
    (void)argc; (void)argv;
#else
    if (argc < 1 || argv == NULL) { corbo_arguments.status = 2; return; }
    size_t count = (size_t)argc - 1;
    if (count > SIZE_MAX / sizeof(corbo_text)) { corbo_arguments.status = 2; return; }
    corbo_text *data = count == 0 ? NULL : (corbo_text *)corbo_stack_alloc(count * sizeof(corbo_text), alignof(corbo_text));
    for (size_t at = 0; at < count; ++at) {
        if (argv[at + 1] == NULL) { corbo_arguments.status = 2; return; }
        size_t length = strlen(argv[at + 1]);
        if (!corbo_utf8_valid((const uint8_t *)argv[at + 1], length)) { corbo_arguments.status = 1; return; }
        ::new (&data[at]) corbo_text{(uint8_t *)argv[at + 1], length};
    }
    corbo_arguments.data = data; corbo_arguments.len = count;
#endif
}
#endif
