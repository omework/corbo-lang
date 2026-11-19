#ifdef _WIN32
#include <windows.h>
#include <shellapi.h>
#endif

static CrustSlice crust_args;
static unsigned crust_args_status;

#ifndef _WIN32
// Match the UTF-8 scalar ranges, including the restricted second octet.
static int crust_arg_valid_utf8(const unsigned char *text, size_t length) {
    for (size_t i = 0; i < length;) {
        unsigned lead = text[i++];
        if (lead < 0x80)
            continue;
        size_t extra = lead >= 0xc2 && lead <= 0xdf ? 1 :
                       lead >= 0xe0 && lead <= 0xef ? 2 :
                       lead >= 0xf0 && lead <= 0xf4 ? 3 : 0;
        if (extra == 0 || extra > length - i)
            return 0;
        unsigned second = text[i];
        if ((lead == 0xe0 && second < 0xa0) || (lead == 0xed && second >= 0xa0) ||
            (lead == 0xf0 && second < 0x90) || (lead == 0xf4 && second >= 0x90))
            return 0;
        for (size_t j = 0; j < extra; ++j)
            if ((text[i++] & 0xc0) != 0x80)
                return 0;
    }
    return 1;
}
#endif

static void crust_args_init(int argc, char **argv) {
#ifdef _WIN32
    (void)argv;
    wchar_t **wide = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (wide == NULL) {
        crust_args_status = 2;
        return;
    }
#endif
    size_t count = argc > 0 ? (size_t)argc - 1 : 0;
    CrustSlice *items = count ? calloc(count, sizeof(*items)) : NULL;
    if (count && items == NULL)
        crust_args_status = 2;
    for (size_t i = 0; i < count && crust_args_status == 0; ++i) {
#ifdef _WIN32
        int length = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide[i + 1], -1,
                                         NULL, 0, NULL, NULL);
        if (length == 0) {
            crust_args_status = GetLastError() == ERROR_NO_UNICODE_TRANSLATION ? 1 : 2;
            break;
        }
        char *bytes = malloc((size_t)length);
        if (bytes == NULL) {
            crust_args_status = 2;
            break;
        }
        if (WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide[i + 1], -1,
                                bytes, length, NULL, NULL) == 0) {
            crust_args_status = GetLastError() == ERROR_NO_UNICODE_TRANSLATION ? 1 : 2;
            free(bytes);
            break;
        }
        items[i] = (CrustSlice){bytes, (size_t)length - 1};
#else
        size_t length = strlen(argv[i + 1]);
        if (!crust_arg_valid_utf8((const unsigned char *)argv[i + 1], length)) {
            crust_args_status = 1;
            break;
        }
        items[i] = (CrustSlice){argv[i + 1], length};
#endif
    }
#ifdef _WIN32
    LocalFree(wide);
#endif
    if (crust_args_status == 0) {
        crust_args = (CrustSlice){items, count};
    } else {
#ifdef _WIN32
        if (items != NULL)
            for (size_t i = 0; i < count; ++i)
                free((void *)items[i].data);
#endif
        free(items);
    }
}
