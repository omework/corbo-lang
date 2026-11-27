// SPDX-License-Identifier: MIT OR Apache-2.0
#ifndef CORBO_CPP_TEXT_HPP
#define CORBO_CPP_TEXT_HPP
// Validate Unicode scalar encodings without copying or modifying input bytes.
static inline bool corbo_utf8_valid(const uint8_t *data, size_t length) {
    for (size_t at = 0; at < length;) {
        uint8_t first = data[at++];
        if (first < 128) continue;
        size_t count;
        if (first >= 194 && first <= 223) count = 1;
        else if (first >= 224 && first <= 239) count = 2;
        else if (first >= 240 && first <= 244) count = 3;
        else return false;
        if (count > length - at) return false;
        uint8_t next = data[at];
        if ((first == 224 && next < 160) || (first == 237 && next >= 160)
            || (first == 240 && next < 144) || (first == 244 && next >= 144)) return false;
        for (size_t index = 0; index < count; ++index)
            if ((data[at++] & 192) != 128) return false;
    }
    return true;
}
#endif
