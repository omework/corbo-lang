//! Source-only lexical analysis. No declarations, types, targets or language
//! rules are consulted here. All spans are half-open UTF-8 byte offsets.
use crate::{Error, Span};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    /// Identifier-shaped spelling, including keywords. The parser distinguishes
    /// keyword terminals by spelling, not by looking up a declaration.
    Name,
    Integer,
    Float,
    Text,
    Punct,
    Assembly,
    C,
    Cpp,
    Eof,
}

/// A foreign-language island remains text; operands are lexical placeholders,
/// not resolved bindings. Header includes/options are preserved, not interpreted.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ForeignBlock {
    pub header: Span,
    /// Already-tokenized Corbo header, using original-source offsets.
    pub header_tokens: Vec<Token>,
    pub body: Span,
    pub operands: Vec<Span>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Payload {
    /// Exact spelling is available through Token::text, with no numeric type
    /// inference, overflow checks or interpretation of identifier names.
    Source,
    /// UTF-8 bytes decoded once using the language's JSON string escapes.
    Text(Vec<u8>),
    Foreign(ForeignBlock),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Token {
    pub kind: Kind,
    pub span: Span,
    pub payload: Payload,
}

impl Token {
    /// Borrow the exact source spelling; source must be the original input.
    pub fn text<'a>(&self, source: &'a str) -> &'a str {
        &source[self.span.start..self.span.end]
    }
}

/// Scan source into tokens, retaining an explicit EOF token even for empty input.
/// Syntactically/semantically invalid programs can still have valid tokens.
pub fn lex(source: &str) -> Result<Vec<Token>, Error> {
    let bytes = source.as_bytes();
    let mut tokens = Vec::new();
    let mut cursor = 0;
    while cursor < bytes.len() {
        let start = cursor;
        let byte = bytes[cursor];
        if byte.is_ascii_whitespace() {
            cursor += 1;
            continue;
        }
        let tail = &source[start..];
        if tail.starts_with("//") {
            cursor += tail.find('\n').unwrap_or(tail.len());
            continue;
        }
        let foreign = if foreign_prefix(tail, "@asm") {
            Some((Kind::Assembly, 4))
        } else if foreign_prefix(tail, "@c++") {
            Some((Kind::Cpp, 4))
        } else if foreign_prefix(tail, "@c") {
            Some((Kind::C, 2))
        } else {
            None
        };
        if let Some((kind, width)) = foreign {
            let (end, block) = foreign_block(source, start, start + width)?;
            tokens.push(Token {
                kind,
                span: Span { start, end },
                payload: Payload::Foreign(block),
            });
            cursor = end;
            continue;
        }
        let after_dot = tokens.last().is_some_and(|t| t.text(source) == ".");
        let leading_float = byte == b'.'
            && bytes.get(cursor + 1).is_some_and(u8::is_ascii_digit)
            && !tokens.last().is_some_and(|t| ends_value(t, source));
        let kind = match byte {
            b'a'..=b'z' | b'A'..=b'Z' | b'_' => {
                cursor += 1;
                while bytes
                    .get(cursor)
                    .is_some_and(|b| b.is_ascii_alphanumeric() || *b == b'_')
                {
                    cursor += 1;
                }
                Kind::Name
            }
            b'"' => {
                cursor = string_end(bytes, start)?;
                Kind::Text
            }
            b'0' if tail.starts_with("0x") || tail.starts_with("0X") => {
                cursor += 2;
                let digits = cursor;
                while bytes.get(cursor).is_some_and(u8::is_ascii_hexdigit) {
                    cursor += 1;
                }
                if cursor == digits {
                    return Err(Error::new(start, "hexadecimal integer requires digits"));
                }
                Kind::Integer
            }
            b'0'..=b'9' | b'.' if byte != b'.' || leading_float => {
                while bytes.get(cursor).is_some_and(u8::is_ascii_digit) {
                    cursor += 1;
                }
                if !after_dot
                    && bytes.get(cursor) == Some(&b'.')
                    && bytes.get(cursor + 1) != Some(&b'.')
                {
                    cursor += 1;
                    while bytes.get(cursor).is_some_and(u8::is_ascii_digit) {
                        cursor += 1;
                    }
                    Kind::Float
                } else {
                    Kind::Integer
                }
            }
            _ => {
                // Longest match first. Never split >>/>>= based on type context;
                // splitting a generic closer is a later parser responsibility.
                const OPERATORS: &[&str] = &[
                    "<<=", ">>=", "::", "->", "=>", "..", "==", "!=", "<=", ">=", "&&", "||", "<<",
                    ">>", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
                ];
                if let Some(op) = OPERATORS.iter().find(|op| tail.starts_with(**op)) {
                    cursor += op.len();
                } else if b"{}()[]<>,:;.#=+-*/%&|^!~@?".contains(&byte) {
                    cursor += 1;
                } else {
                    return Err(Error::new(start, "unexpected character in Corbo source"));
                }
                Kind::Punct
            }
        };
        let payload = if kind == Kind::Text {
            Payload::Text(decoded_text(&source[start..cursor]))
        } else {
            Payload::Source
        };
        tokens.push(Token {
            kind,
            span: Span { start, end: cursor },
            payload,
        });
    }
    tokens.push(Token {
        kind: Kind::Eof,
        span: Span {
            start: cursor,
            end: cursor,
        },
        payload: Payload::Source,
    });
    Ok(tokens)
}

// A dot after a value introduces a field, not a leading-dot floating literal.
// This uses only preceding token spelling; it never consults bindings or types.
fn ends_value(token: &Token, source: &str) -> bool {
    match token.kind {
        Kind::Integer | Kind::Float | Kind::Text => true,
        Kind::Name => !matches!(
            token.text(source),
            "return"
                | "break"
                | "if"
                | "else"
                | "while"
                | "match"
                | "in"
                | "let"
                | "mut"
                | "move"
                | "async"
        ),
        Kind::Punct => matches!(token.text(source), ")" | "]" | "}" | "?" | "!"),
        _ => false,
    }
}

fn foreign_prefix(tail: &str, prefix: &str) -> bool {
    tail.strip_prefix(prefix).is_some_and(|rest| {
        rest.as_bytes()
            .first()
            .is_none_or(|b| !b.is_ascii_alphanumeric() && *b != b'_')
    })
}

// Find the lexical island after an optional parenthesized header. Header tokens
// are not interpreted as includes, types or bindings by this scanner.
fn foreign_block(
    source: &str,
    start: usize,
    mut at: usize,
) -> Result<(usize, ForeignBlock), Error> {
    let bytes = source.as_bytes();
    let header_start = at;
    let mut parens = 0usize;
    while at < bytes.len() {
        if let Some(end) = foreign_quoted_or_comment(source, at)? {
            at = end;
            continue;
        }
        match bytes[at] {
            b'(' => parens += 1,
            b')' if parens > 0 => parens -= 1,
            b'{' if parens == 0 => break,
            _ => {}
        }
        at += 1;
    }
    if at == bytes.len() {
        return Err(Error::new(start, "foreign block has no opening brace"));
    }
    let header = Span {
        start: header_start,
        end: at,
    };
    let mut header_tokens = lex(&source[header.start..header.end]).map_err(|mut error| {
        error.offset += header.start;
        error.related_offset = error.related_offset.map(|offset| offset + header.start);
        error
    })?;
    for token in &mut header_tokens {
        shift_token(token, header.start);
    }
    let body_start = at + 1;
    at = body_start;
    let mut depth = 1usize;
    let mut operands = Vec::new();
    while at < bytes.len() {
        if let Some(end) = foreign_quoted_or_comment(source, at)? {
            at = end;
            continue;
        }
        if bytes.get(at..at + 2) == Some(b"${") {
            let name_start = at + 2;
            let Some(relative_end) = source[name_start..].find('}') else {
                return Err(Error::new(at, "unterminated foreign operand"));
            };
            let end = name_start + relative_end;
            let mut name = bytes[name_start..end].iter();
            if !name
                .next()
                .is_some_and(|b| b.is_ascii_alphabetic() || *b == b'_')
                || !name.all(|b| b.is_ascii_alphanumeric() || *b == b'_')
            {
                return Err(Error::new(
                    name_start,
                    "foreign operand must be an identifier",
                ));
            }
            operands.push(Span {
                start: name_start,
                end,
            });
            at = end + 1;
            continue;
        }
        match bytes[at] {
            b'{' => depth += 1,
            b'}' => {
                depth -= 1;
                if depth == 0 {
                    return Ok((
                        at + 1,
                        ForeignBlock {
                            header,
                            header_tokens,
                            body: Span {
                                start: body_start,
                                end: at,
                            },
                            operands,
                        },
                    ));
                }
            }
            _ => {}
        }
        at += 1;
    }
    Err(Error::new(start, "unterminated foreign block"))
}

// Header tokenization uses a source slice; publish only original-source spans.
fn shift_token(token: &mut Token, base: usize) {
    token.span.start += base;
    token.span.end += base;
    if let Payload::Foreign(block) = &mut token.payload {
        block.header.start += base;
        block.header.end += base;
        block.body.start += base;
        block.body.end += base;
        for operand in &mut block.operands {
            operand.start += base;
            operand.end += base;
        }
        for token in &mut block.header_tokens {
            shift_token(token, base);
        }
    }
}

// Foreign strings/comments shield braces and ${...}. Raw C++ strings are
// recognized without decoding or otherwise interpreting the foreign language.
fn foreign_quoted_or_comment(source: &str, at: usize) -> Result<Option<usize>, Error> {
    let bytes = source.as_bytes();
    if bytes.get(at..at + 2) == Some(b"//") {
        return Ok(Some(
            at + bytes[at..]
                .iter()
                .position(|b| *b == b'\n')
                .unwrap_or(bytes.len() - at),
        ));
    }
    if bytes.get(at..at + 2) == Some(b"/*") {
        let end = bytes[at + 2..]
            .windows(2)
            .position(|s| s == b"*/")
            .ok_or_else(|| Error::new(at, "unterminated foreign block comment"))?;
        return Ok(Some(at + 2 + end + 2));
    }
    if bytes.get(at..at + 2) == Some(b"R\"") {
        let open = bytes[at + 2..]
            .iter()
            .position(|b| *b == b'(')
            .ok_or_else(|| Error::new(at, "unterminated C++ raw string"))?
            + at
            + 2;
        let delimiter = &bytes[at + 2..open];
        let mut closing = vec![b')'];
        closing.extend_from_slice(delimiter);
        closing.push(b'"');
        let end = bytes[open + 1..]
            .windows(closing.len())
            .position(|s| s == closing)
            .ok_or_else(|| Error::new(at, "unterminated C++ raw string"))?;
        return Ok(Some(open + 1 + end + closing.len()));
    }
    if matches!(bytes.get(at), Some(b'"' | b'\'')) {
        let quote = bytes[at];
        let mut end = at + 1;
        while end < bytes.len() {
            if bytes[end] == quote {
                return Ok(Some(end + 1));
            }
            if bytes[end] == b'\\' {
                end += 1;
            }
            end += 1;
        }
        return Err(Error::new(at, "unterminated foreign quoted literal"));
    }
    Ok(None)
}

fn string_end(bytes: &[u8], start: usize) -> Result<usize, Error> {
    let mut i = start + 1;
    while let Some(&byte) = bytes.get(i) {
        match byte {
            b'"' => return Ok(i + 1),
            0..=31 => return Err(Error::new(i, "control character in string literal")),
            b'\\' => {
                i += 1;
                match bytes.get(i) {
                    Some(b'"' | b'\\' | b'/' | b'b' | b'f' | b'n' | b'r' | b't') => {}
                    Some(b'u') => {
                        let marker = i;
                        let first = hex_unit(bytes, i)?;
                        i += 4;
                        if (0xd800..=0xdbff).contains(&first) {
                            if bytes.get(i + 1..i + 3) != Some(b"\\u") {
                                return Err(Error::new(marker, "incomplete UTF-16 surrogate pair"));
                            }
                            let second = hex_unit(bytes, i + 2)?;
                            if !(0xdc00..=0xdfff).contains(&second) {
                                return Err(Error::new(i + 2, "invalid UTF-16 surrogate pair"));
                            }
                            i += 6;
                        } else if (0xdc00..=0xdfff).contains(&first) {
                            return Err(Error::new(marker, "isolated UTF-16 surrogate"));
                        }
                    }
                    _ => return Err(Error::new(i, "invalid string escape")),
                }
            }
            _ => {}
        }
        i += 1;
    }
    Err(Error::new(start, "unterminated string literal"))
}

fn hex_unit(bytes: &[u8], marker: usize) -> Result<u16, Error> {
    let digits = bytes
        .get(marker + 1..marker + 5)
        .filter(|s| s.iter().all(u8::is_ascii_hexdigit))
        .ok_or_else(|| Error::new(marker, "invalid Unicode escape"))?;
    Ok(digits.iter().fold(0, |value, digit| {
        value * 16
            + u16::from(if digit.is_ascii_digit() {
                digit - b'0'
            } else {
                digit.to_ascii_lowercase() - b'a' + 10
            })
    }))
}

/// Decode a text token after the lexer has validated its JSON escapes.
pub(crate) fn decoded_text(text: &str) -> Vec<u8> {
    let bytes = text.as_bytes();
    let mut output = Vec::new();
    let mut cursor = 1;
    while cursor + 1 < bytes.len() {
        let byte = bytes[cursor];
        cursor += 1;
        if byte != b'\\' {
            output.push(byte);
            continue;
        }
        let escaped = bytes[cursor];
        cursor += 1;
        output.push(match escaped {
            b'b' => 8,
            b'f' => 12,
            b'n' => b'\n',
            b'r' => b'\r',
            b't' => b'\t',
            b'u' => {
                let first = u32::from(hex_unit(bytes, cursor - 1).unwrap());
                cursor += 4;
                let codepoint = if (0xd800..=0xdbff).contains(&first) {
                    let second = u32::from(hex_unit(bytes, cursor + 1).unwrap());
                    cursor += 6;
                    0x10000 + ((first - 0xd800) << 10) + second - 0xdc00
                } else {
                    first
                };
                let mut buffer = [0; 4];
                output.extend_from_slice(
                    char::from_u32(codepoint)
                        .unwrap()
                        .encode_utf8(&mut buffer)
                        .as_bytes(),
                );
                continue;
            }
            literal => literal,
        });
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spellings(source: &str) -> Vec<String> {
        lex(source)
            .unwrap()
            .iter()
            .filter(|t| t.kind != Kind::Eof)
            .map(|t| t.text(source).to_owned())
            .collect()
    }

    #[test]
    fn operators_use_longest_match() {
        let ops = [
            "<<=", ">>=", "&=", "|=", "^=", "+=", "-=", "*=", "/=", "%=", "<<", ">>", ">=", "<=",
            "==", "!=", "&&", "||", "::", "=>", "..",
        ];
        assert_eq!(spellings(&ops.join(" ")), ops);
        assert_eq!(
            spellings("T<U<V>> a>>=1"),
            ["T", "<", "U", "<", "V", ">>", "a", ">>=", "1"]
        );
        assert_eq!(spellings("x->y"), ["x", "->", "y"]);
    }

    #[test]
    fn tuple_fields_are_not_floating_literals() {
        assert_eq!(
            spellings("self.buffer[i].0.1 slot.0"),
            [
                "self", ".", "buffer", "[", "i", "]", ".", "0", ".", "1", "slot", ".", "0"
            ]
        );
    }

    #[test]
    fn decimal_literals_and_ranges_stay_separate() {
        let source = "1.5 1. .5; return .5; 1..3 &[..2] -0xFF";
        assert_eq!(
            spellings(source),
            [
                "1.5", "1.", ".", "5", ";", "return", ".5", ";", "1", "..", "3", "&", "[", "..",
                "2", "]", "-", "0xFF"
            ]
        );
        for source in [".5", "let x = .5", "return .5", "f(.5)"] {
            assert!(
                lex(source)
                    .unwrap()
                    .iter()
                    .any(|t| t.kind == Kind::Float && t.text(source) == ".5")
            );
        }
    }

    #[test]
    fn strings_pass_decoded_bytes_and_original_spelling() {
        let source = r#""é\uD83D\uDE00\n\t\/\"\\\b\f\r""#;
        let tokens = lex(source).unwrap();
        assert_eq!(tokens[0].text(source), source);
        assert_eq!(
            tokens[0].payload,
            Payload::Text("é😀\n\t/\"\\\u{8}\u{c}\r".as_bytes().to_vec())
        );
        assert_eq!(
            tokens[1].span,
            Span {
                start: source.len(),
                end: source.len()
            }
        );
    }

    #[test]
    fn lexical_errors_have_exact_byte_offsets() {
        for (source, offset) in [
            ("0x", 0),
            ("\"a\\q\"", 3),
            ("\"a\n\"", 2),
            ("\"\\uDC00\"", 2),
            ("\"unfinished", 0),
            ("\"é\" $", 5),
        ] {
            assert_eq!(lex(source).unwrap_err().offset, offset, "{source}");
        }
    }

    #[test]
    fn cpp_is_opaque_with_nested_braces_strings_and_operands() {
        let source = r##"@unchecked { @c++(includes={"a.hpp"}) {
            if (true) { char c = '}'; const char* s = "${ignored}}"; }
            /* } ${ignored} */ // } ${ignored}
            const char* raw = R"tag(} ${ignored} " )tag";
            *${number_addr} = 20;
        } }"##;
        let tokens = lex(source).unwrap();
        let token = tokens.iter().find(|t| t.kind == Kind::Cpp).unwrap();
        let Payload::Foreign(block) = &token.payload else {
            panic!("missing payload")
        };
        assert_eq!(
            &source[block.header.start..block.header.end],
            "(includes={\"a.hpp\"}) "
        );
        assert_eq!(
            block
                .header_tokens
                .iter()
                .filter(|t| t.kind != Kind::Eof)
                .map(|t| t.text(source))
                .collect::<Vec<_>>(),
            ["(", "includes", "=", "{", "\"a.hpp\"", "}", ")"]
        );
        assert_eq!(block.operands.len(), 1);
        assert_eq!(
            &source[block.operands[0].start..block.operands[0].end],
            "number_addr"
        );
        assert!(source[block.body.start..block.body.end].contains("if (true)"));
        assert_eq!(tokens[tokens.len() - 2].text(source), "}");
    }

    #[test]
    fn c_preserves_headers_nested_braces_and_operand_spans() {
        let source = r#"@unchecked { @c(includes={"stdint.h"}) {
            /* } ${ignored} */
            const char *s = "} ${ignored}";
            if (1) { *${address} = 20; }
        } }"#;
        let tokens = lex(source).unwrap();
        let token = tokens.iter().find(|t| t.kind == Kind::C).unwrap();
        let Payload::Foreign(block) = &token.payload else {
            panic!("missing payload")
        };
        assert_eq!(
            token.text(source),
            &source[token.span.start..token.span.end]
        );
        assert_eq!(
            &source[block.header.start..block.header.end],
            "(includes={\"stdint.h\"}) "
        );
        assert!(block.header_tokens.iter().any(|t| matches!(&t.payload,
            Payload::Text(bytes) if bytes == b"stdint.h")));
        assert_eq!(block.operands.len(), 1);
        assert_eq!(
            &source[block.operands[0].start..block.operands[0].end],
            "address"
        );
        assert!(source[block.body.start..block.body.end].contains("*${address} = 20;"));
        assert_eq!(tokens[tokens.len() - 2].text(source), "}");
    }

    #[test]
    fn foreign_markers_remain_distinct_without_checking_unchecked_enclosure() {
        let source = "@c {} @c++ {} @asm {}";
        assert_eq!(
            lex(source)
                .unwrap()
                .iter()
                .map(|t| t.kind)
                .collect::<Vec<_>>(),
            [Kind::C, Kind::Cpp, Kind::Assembly, Kind::Eof]
        );
        assert_eq!(spellings("@c_name"), ["@", "c_name"]);
        assert!(lex("@c { /* unclosed").is_err());
        assert!(lex("@c { \"unclosed").is_err());
    }

    #[test]
    fn asm_preserves_text_without_checking_scope_or_target() {
        let source = "@asm /* marker trivia */ { mov x0, ${address}\n // }\n ret }";
        let tokens = lex(source).unwrap();
        assert_eq!(tokens[0].kind, Kind::Assembly);
        let Payload::Foreign(block) = &tokens[0].payload else {
            panic!("missing payload")
        };
        assert_eq!(
            &source[block.operands[0].start..block.operands[0].end],
            "address"
        );
        assert!(lex("@asm { unknown_instruction }").is_ok());
        assert_eq!(spellings("@asm_name"), ["@", "asm_name"]);
    }

    #[test]
    fn foreign_delimiter_errors_are_lexical() {
        for source in [
            "@asm {",
            "@c++ { /*",
            "@c++ { \"",
            "@asm { ${}",
            "@asm { ${not a name} }",
            "@c++ { R\"tag(unclosed",
        ] {
            assert!(lex(source).is_err(), "{source}");
        }
    }

    #[test]
    fn lexing_does_not_resolve_or_verify_anything() {
        let source = "async move { missing_private_name.unknown = \"wrong type\"; }";
        let tokens = lex(source).unwrap();
        assert_eq!(tokens[0].kind, Kind::Name);
        assert_eq!(tokens[0].text(source), "async");
        assert!(spellings(source).contains(&"missing_private_name".to_owned()));
        assert!(lex("return not_declared; break; yield;").is_ok());
    }

    #[test]
    fn spans_reference_the_unmodified_source() {
        let source = "// é\r\nlet number = \"été\"; // fin";
        let tokens = lex(source).unwrap();
        let expected = ["let", "number", "=", "\"été\"", ";", ""];
        let mut end = 0;
        for (token, text) in tokens.iter().zip(expected) {
            assert_eq!(token.text(source), text);
            assert!(token.span.start >= end);
            assert!(source.is_char_boundary(token.span.start));
            assert!(source.is_char_boundary(token.span.end));
            end = token.span.end;
        }
        assert_eq!(tokens.len(), expected.len());
        assert_eq!(lex("").unwrap()[0].span, Span { start: 0, end: 0 });
    }
}
