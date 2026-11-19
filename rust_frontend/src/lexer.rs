use crate::{Error, Span};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    Name,
    Integer,
    Float,
    Text,
    Punct,
    Assembly,
    Eof,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Token {
    pub kind: Kind,
    pub span: Span,
}

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
        if let Some(tail) = tail.strip_prefix("@asm") {
            let padding = tail.len() - tail.trim_start().len();
            if tail.trim_start().starts_with('{') {
                let body = start + "@asm".len() + padding + 1;
                cursor = assembly_end(source, body)?;
                tokens.push(Token {
                    kind: Kind::Assembly,
                    span: Span { start, end: cursor },
                });
                continue;
            }
        }
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
                    return Err(Error::new(start, "entier hexadécimal sans chiffres"));
                }
                Kind::Integer
            }
            b'0'..=b'9' | b'.'
                if byte != b'.' || bytes.get(cursor + 1).is_some_and(u8::is_ascii_digit) =>
            {
                while bytes.get(cursor).is_some_and(u8::is_ascii_digit) {
                    cursor += 1;
                }
                if bytes.get(cursor) == Some(&b'.') && bytes.get(cursor + 1) != Some(&b'.') {
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
                const PUNCTUATION: [&str; 19] = [
                    "<<=", "&=", "|=", "^=", "::", "->", "=>", "..", "==", "!=", "<=", "&&", "||", "<<", "+=", "-=", "*=",
                    "/=", "%=",
                ];
                if let Some(op) = PUNCTUATION.iter().find(|op| tail.starts_with(**op)) {
                    cursor += op.len();
                } else if b"{}()[]<>,:;.#=+-*/%&|^!~@?".contains(&byte) {
                    cursor += 1;
                } else {
                    return Err(Error::new(start, "caractère inattendu"));
                }
                Kind::Punct
            }
        };
        tokens.push(Token {
            kind,
            span: Span { start, end: cursor },
        });
    }
    tokens.push(Token {
        kind: Kind::Eof,
        span: Span {
            start: cursor,
            end: cursor,
        },
    });
    Ok(tokens)
}

// Preserve whitespace and comments in the assembly template. Skip the
// closing brace of an interpolated operand when looking for the block end.
fn assembly_end(source: &str, mut cursor: usize) -> Result<usize, Error> {
    while let Some(&byte) = source.as_bytes().get(cursor) {
        match byte {
            b'}' => return Ok(cursor + 1),
            b'$' if source.as_bytes().get(cursor + 1) == Some(&b'{') => {
                let operand = cursor + 2;
                cursor = source[operand..].find('}')
                    .map(|end| operand + end)
                    .ok_or_else(|| Error::new(cursor, "opérande assembleur non fermé"))?;
                let mut name = source[operand..cursor].bytes();
                if !name.next().is_some_and(|b| b.is_ascii_alphabetic() || b == b'_')
                    || !name.all(|b| b.is_ascii_alphanumeric() || b == b'_')
                {
                    return Err(Error::new(operand, "nom d’opérande assembleur invalide"));
                }
            }
            b'/' if source.as_bytes().get(cursor + 1) == Some(&b'/') => {
                cursor += source[cursor..].find('\n').unwrap_or(source.len() - cursor);
                continue;
            }
            _ => {}
        }
        cursor += 1;
    }
    Err(Error::new(cursor, "bloc assembleur non fermé"))
}

fn string_end(bytes: &[u8], start: usize) -> Result<usize, Error> {
    let mut i = start + 1;
    while let Some(&byte) = bytes.get(i) {
        match byte {
            b'"' => return Ok(i + 1),
            0..=31 => return Err(Error::new(i, "caractère de contrôle dans un texte")),
            b'\\' => {
                i += 1;
                match bytes.get(i) {
                    Some(b'"' | b'\\' | b'/' | b'b' | b'f' | b'n' | b'r' | b't') => {}
                    Some(b'u') => {
                        let first = hex_unit(bytes, i)?;
                        i += 4;
                        if (0xd800..=0xdbff).contains(&first) {
                            if bytes.get(i + 1..i + 3) != Some(b"\\u") {
                                return Err(Error::new(i, "paire UTF-16 incomplète"));
                            }
                            let second = hex_unit(bytes, i + 2)?;
                            if !(0xdc00..=0xdfff).contains(&second) {
                                return Err(Error::new(i + 2, "paire UTF-16 invalide"));
                            }
                            i += 6;
                        } else if (0xdc00..=0xdfff).contains(&first) {
                            return Err(Error::new(i, "surrogate isolé"));
                        }
                    }
                    _ => return Err(Error::new(i, "échappement inconnu")),
                }
            }
            _ => {}
        }
        i += 1;
    }
    Err(Error::new(start, "texte non fermé"))
}

fn hex_unit(bytes: &[u8], marker: usize) -> Result<u16, Error> {
    let digits = bytes
        .get(marker + 1..marker + 5)
        .filter(|s| s.iter().all(u8::is_ascii_hexdigit))
        .ok_or_else(|| Error::new(marker, "échappement Unicode invalide"))?;
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
