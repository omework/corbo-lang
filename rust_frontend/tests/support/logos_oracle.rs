//! Independent test oracle: generated Logos rules + serde_json decoding.
//! No production lexer helpers, token types or diagnostics are used here.
use logos::Logos;
use std::ops::Range;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Data {
    Raw,
    Text(Vec<u8>),
    Island {
        header: Range<usize>,
        body: Range<usize>,
        operands: Vec<Range<usize>>,
        header_tokens: Vec<Token>,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Token {
    pub class: &'static str,
    pub range: Range<usize>,
    pub data: Data,
}

#[derive(Debug)]
pub struct Fault {
    pub category: &'static str,
    pub range: Range<usize>,
}

#[derive(Logos, Debug, PartialEq)]
#[logos(skip r"[ \t\r\n\x0B\x0C]+")]
#[logos(skip(r"//[^\n]*", allow_greedy = true))]
enum Ordinary {
    #[regex(r"[A-Za-z_][A-Za-z_0-9]*")]
    Word,
    #[regex(r"0[xX][0-9a-fA-F]*", priority = 3)]
    Hex,
    #[regex(r"[0-9]+")]
    Decimal,
    #[regex(r#""([^"\\]|\\[\s\S])*""#, priority = 3)]
    String,
    #[token("\"")]
    UnfinishedString,
    #[regex(r"<<=|>>=|::|->|=>|\.\.|==|!=|<=|>=|&&|\|\||<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=")]
    #[regex(r"[{}()\[\]<>,:;.#=+*/%&|^!~@?\-]")]
    Symbol,
}

// A second generated lexer handles foreign lexical modes. Nested braces and
// raw-string delimiters are handled as state, not copied production scans.
#[derive(Logos, Debug, PartialEq)]
enum Foreign {
    #[regex(r"//[^\n]*", priority = 5, allow_greedy = true)]
    #[regex(r"/\*([^*]|\*+[^*/])*\*+/", priority = 5)]
    Comment,
    #[regex(r#""([^"\\]|\\[\s\S])*""#, priority = 4)]
    #[regex(r"'([^'\\]|\\[\s\S])*'", priority = 4)]
    Quoted,
    #[token("R\"", priority = 6)]
    RawString,
    #[regex(r"\$\{[A-Za-z_][A-Za-z_0-9]*\}", priority = 5)]
    Operand,
    #[token("${", priority = 4)]
    BadOperand,
    #[token("/*", priority = 3)]
    BadComment,
    #[token("\"", priority = 2)]
    #[token("'", priority = 2)]
    BadQuote,
    #[token("{")]
    Open,
    #[token("}")]
    Close,
    #[token("(")]
    ParenOpen,
    #[token(")")]
    ParenClose,
    #[regex(r#"[^{}()"'/$R]+"#, priority = 1)]
    #[regex(r"[\s\S]", priority = 0)]
    Other,
}

fn fault(category: &'static str, range: Range<usize>) -> Fault {
    Fault { category, range }
}

fn shift(token: &mut Token, amount: usize) {
    token.range = token.range.start + amount..token.range.end + amount;
    if let Data::Island {
        header,
        body,
        operands,
        header_tokens,
    } = &mut token.data
    {
        *header = header.start + amount..header.end + amount;
        *body = body.start + amount..body.end + amount;
        for range in operands {
            *range = range.start + amount..range.end + amount;
        }
        for token in header_tokens {
            shift(token, amount);
        }
    }
}

fn scan_island(
    source: &str,
    marker_start: usize,
    header_start: usize,
) -> Result<(usize, Data), Fault> {
    let mut scanner = Foreign::lexer(&source[header_start..]);
    let mut parentheses = 0;
    let mut braces = 0;
    let mut body_start = None;
    let mut operands = Vec::new();
    while let Some(item) = scanner.next() {
        let range = header_start + scanner.span().start..header_start + scanner.span().end;
        let item = item.map_err(|_| fault("foreign", range.clone()))?;
        match item {
            Foreign::BadComment | Foreign::BadQuote | Foreign::BadOperand => {
                return Err(fault("foreign", range.start..source.len()));
            }
            Foreign::RawString => {
                let rest = scanner.remainder();
                let Some((delimiter, contents)) = rest.split_once('(') else {
                    return Err(fault("foreign", range.start..source.len()));
                };
                let closing = format!("){delimiter}\"");
                let end = contents
                    .find(&closing)
                    .ok_or_else(|| fault("foreign", range.start..source.len()))?;
                scanner.bump(delimiter.len() + 1 + end + closing.len());
            }
            Foreign::ParenOpen if body_start.is_none() => parentheses += 1,
            Foreign::ParenClose if body_start.is_none() && parentheses > 0 => parentheses -= 1,
            Foreign::Open if body_start.is_none() && parentheses == 0 => {
                body_start = Some(range.end);
                braces = 1;
            }
            Foreign::Open if body_start.is_some() => braces += 1,
            Foreign::Close if body_start.is_some() => {
                braces -= 1;
                if braces == 0 {
                    let begin = body_start.unwrap();
                    let header = header_start..begin - 1;
                    let mut header_tokens =
                        scan(&source[header.clone()]).map_err(|mut error| {
                            error.range =
                                error.range.start + header_start..error.range.end + header_start;
                            error
                        })?;
                    for token in &mut header_tokens {
                        shift(token, header_start);
                    }
                    return Ok((
                        range.end,
                        Data::Island {
                            header,
                            body: begin..range.start,
                            operands,
                            header_tokens,
                        },
                    ));
                }
            }
            Foreign::Operand if body_start.is_some() => {
                operands.push(range.start + 2..range.end - 1)
            }
            _ => {}
        }
    }
    Err(fault("foreign", marker_start..source.len()))
}

/// Build independent, normalized tokens; raw numeric spellings remain untyped.
pub fn scan(source: &str) -> Result<Vec<Token>, Fault> {
    let mut scanner = Ordinary::lexer(source);
    let mut output: Vec<Token> = Vec::new();
    let mut follows_value = false;
    let mut field_digits = false;
    while let Some(item) = scanner.next() {
        let mut range = scanner.span();
        let item = item.map_err(|_| fault("character", range.clone()))?;
        let spelling = scanner.slice();
        let previous_field = field_digits;
        field_digits = false;
        let mut data = Data::Raw;
        let class = match item {
            Ordinary::Word => {
                follows_value = ![
                    "return", "break", "if", "else", "while", "match", "in", "let", "mut", "move",
                    "async",
                ]
                .contains(&spelling);
                "word"
            }
            Ordinary::String => {
                let decoded: String =
                    serde_json::from_str(spelling).map_err(|_| fault("string", range.clone()))?;
                data = Data::Text(decoded.into_bytes());
                follows_value = true;
                "text"
            }
            Ordinary::UnfinishedString => return Err(fault("string", range.start..source.len())),
            Ordinary::Hex => {
                if spelling.len() == 2 {
                    return Err(fault("number", range));
                }
                follows_value = true;
                "integer"
            }
            Ordinary::Decimal => {
                let rest = scanner.remainder();
                let fraction = !previous_field && rest.starts_with('.') && !rest.starts_with("..");
                if fraction {
                    let width = 1 + rest[1..].bytes().take_while(u8::is_ascii_digit).count();
                    scanner.bump(width);
                    range.end += width;
                }
                follows_value = true;
                if fraction { "float" } else { "integer" }
            }
            Ordinary::Symbol
                if spelling == "."
                    && !follows_value
                    && scanner
                        .remainder()
                        .starts_with(|c: char| c.is_ascii_digit()) =>
            {
                let width = scanner
                    .remainder()
                    .bytes()
                    .take_while(u8::is_ascii_digit)
                    .count();
                scanner.bump(width);
                range.end += width;
                follows_value = true;
                "float"
            }
            Ordinary::Symbol if spelling == "@" => {
                let tail = scanner.remainder();
                let marker = [("c++", "cpp"), ("asm", "asm"), ("c", "c")]
                    .into_iter()
                    .find(|(name, _)| {
                        tail.strip_prefix(name).is_some_and(|rest| {
                            !rest.starts_with(|c: char| c.is_ascii_alphanumeric() || c == '_')
                        })
                    });
                follows_value = false;
                if let Some((name, kind)) = marker {
                    let (end, island) = scan_island(source, range.start, range.end + name.len())?;
                    scanner.bump(end - range.end);
                    range.end = end;
                    data = island;
                    kind
                } else {
                    "punct"
                }
            }
            Ordinary::Symbol => {
                field_digits = spelling == ".";
                follows_value = [")", "]", "}", "?", "!"].contains(&spelling);
                "punct"
            }
        };
        output.push(Token { class, range, data });
    }
    output.push(Token {
        class: "eof",
        range: source.len()..source.len(),
        data: Data::Raw,
    });
    Ok(output)
}
