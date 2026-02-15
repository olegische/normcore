use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq)]
pub enum JsonValue {
    Null,
    Bool(bool),
    Number(f64),
    String(String),
    Array(Vec<JsonValue>),
    Object(BTreeMap<String, JsonValue>),
}

impl JsonValue {
    pub fn as_str(&self) -> Option<&str> {
        match self {
            JsonValue::String(s) => Some(s),
            _ => None,
        }
    }

    pub fn as_array(&self) -> Option<&[JsonValue]> {
        match self {
            JsonValue::Array(v) => Some(v),
            _ => None,
        }
    }

    pub fn as_object(&self) -> Option<&BTreeMap<String, JsonValue>> {
        match self {
            JsonValue::Object(m) => Some(m),
            _ => None,
        }
    }

    pub fn get(&self, key: &str) -> Option<&JsonValue> {
        self.as_object().and_then(|m| m.get(key))
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JsonError {
    pub message: String,
}

impl JsonError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

pub fn parse_json(input: &str) -> Result<JsonValue, JsonError> {
    let mut p = Parser {
        bytes: input.as_bytes(),
        i: 0,
    };
    let value = p.parse_value()?;
    p.skip_ws();
    if p.i != p.bytes.len() {
        return Err(JsonError::new("trailing characters in JSON"));
    }
    Ok(value)
}

pub fn to_pretty_json(value: &JsonValue) -> String {
    let mut out = String::new();
    write_value(value, 0, &mut out);
    out
}

fn write_value(value: &JsonValue, indent: usize, out: &mut String) {
    match value {
        JsonValue::Null => out.push_str("null"),
        JsonValue::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        JsonValue::Number(n) => out.push_str(&format_number(*n)),
        JsonValue::String(s) => out.push_str(&quote(s)),
        JsonValue::Array(arr) => {
            if arr.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push_str("[\n");
            for (idx, item) in arr.iter().enumerate() {
                out.push_str(&" ".repeat(indent + 2));
                write_value(item, indent + 2, out);
                if idx + 1 < arr.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            out.push_str(&" ".repeat(indent));
            out.push(']');
        }
        JsonValue::Object(map) => {
            if map.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push_str("{\n");
            let len = map.len();
            for (idx, (k, v)) in map.iter().enumerate() {
                out.push_str(&" ".repeat(indent + 2));
                out.push_str(&quote(k));
                out.push_str(": ");
                write_value(v, indent + 2, out);
                if idx + 1 < len {
                    out.push(',');
                }
                out.push('\n');
            }
            out.push_str(&" ".repeat(indent));
            out.push('}');
        }
    }
}

fn format_number(n: f64) -> String {
    if n.fract() == 0.0 {
        format!("{n:.0}")
    } else {
        n.to_string()
    }
}

fn quote(input: &str) -> String {
    let mut out = String::with_capacity(input.len() + 2);
    out.push('"');
    for c in input.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c.is_control() => out.push_str(&format!("\\u{:04x}", c as u32)),
            _ => out.push(c),
        }
    }
    out.push('"');
    out
}

struct Parser<'a> {
    bytes: &'a [u8],
    i: usize,
}

impl<'a> Parser<'a> {
    fn parse_value(&mut self) -> Result<JsonValue, JsonError> {
        self.skip_ws();
        let b = self
            .peek()
            .ok_or_else(|| JsonError::new("unexpected end of JSON"))?;
        match b {
            b'n' => self.parse_null(),
            b't' | b'f' => self.parse_bool(),
            b'"' => self.parse_string().map(JsonValue::String),
            b'[' => self.parse_array(),
            b'{' => self.parse_object(),
            b'-' | b'0'..=b'9' => self.parse_number().map(JsonValue::Number),
            _ => Err(JsonError::new("unexpected token in JSON")),
        }
    }

    fn parse_null(&mut self) -> Result<JsonValue, JsonError> {
        self.expect_bytes(b"null")?;
        Ok(JsonValue::Null)
    }

    fn parse_bool(&mut self) -> Result<JsonValue, JsonError> {
        if self.consume_bytes(b"true") {
            Ok(JsonValue::Bool(true))
        } else if self.consume_bytes(b"false") {
            Ok(JsonValue::Bool(false))
        } else {
            Err(JsonError::new("invalid boolean"))
        }
    }

    fn parse_string(&mut self) -> Result<String, JsonError> {
        self.expect(b'"')?;
        let mut out = String::new();
        loop {
            let b = self
                .next()
                .ok_or_else(|| JsonError::new("unterminated string"))?;
            match b {
                b'"' => break,
                b'\\' => {
                    let esc = self
                        .next()
                        .ok_or_else(|| JsonError::new("incomplete escape"))?;
                    match esc {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000C}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let code = self.parse_hex4()?;
                            let ch = char::from_u32(code as u32)
                                .ok_or_else(|| JsonError::new("invalid unicode escape"))?;
                            out.push(ch);
                        }
                        _ => return Err(JsonError::new("invalid escape")),
                    }
                }
                b if b.is_ascii_control() => {
                    return Err(JsonError::new("control character in string"));
                }
                _ => out.push(b as char),
            }
        }
        Ok(out)
    }

    fn parse_hex4(&mut self) -> Result<u16, JsonError> {
        let mut value: u16 = 0;
        for _ in 0..4 {
            let b = self
                .next()
                .ok_or_else(|| JsonError::new("truncated unicode escape"))?;
            value <<= 4;
            value |= match b {
                b'0'..=b'9' => (b - b'0') as u16,
                b'a'..=b'f' => (b - b'a' + 10) as u16,
                b'A'..=b'F' => (b - b'A' + 10) as u16,
                _ => return Err(JsonError::new("invalid hex in unicode escape")),
            };
        }
        Ok(value)
    }

    fn parse_array(&mut self) -> Result<JsonValue, JsonError> {
        self.expect(b'[')?;
        self.skip_ws();
        let mut arr = Vec::new();
        if self.try_consume(b']') {
            return Ok(JsonValue::Array(arr));
        }
        loop {
            arr.push(self.parse_value()?);
            self.skip_ws();
            if self.try_consume(b']') {
                break;
            }
            self.expect(b',')?;
        }
        Ok(JsonValue::Array(arr))
    }

    fn parse_object(&mut self) -> Result<JsonValue, JsonError> {
        self.expect(b'{')?;
        self.skip_ws();
        let mut map = BTreeMap::new();
        if self.try_consume(b'}') {
            return Ok(JsonValue::Object(map));
        }
        loop {
            self.skip_ws();
            let key = self.parse_string()?;
            self.skip_ws();
            self.expect(b':')?;
            let value = self.parse_value()?;
            map.insert(key, value);
            self.skip_ws();
            if self.try_consume(b'}') {
                break;
            }
            self.expect(b',')?;
        }
        Ok(JsonValue::Object(map))
    }

    fn parse_number(&mut self) -> Result<f64, JsonError> {
        let start = self.i;
        self.try_consume(b'-');
        self.consume_digits();
        if self.try_consume(b'.') {
            self.consume_digits();
        }
        if let Some(b'e' | b'E') = self.peek() {
            self.i += 1;
            if let Some(b'+' | b'-') = self.peek() {
                self.i += 1;
            }
            self.consume_digits();
        }
        let s = std::str::from_utf8(&self.bytes[start..self.i])
            .map_err(|_| JsonError::new("invalid number encoding"))?;
        s.parse::<f64>()
            .map_err(|_| JsonError::new("invalid number literal"))
    }

    fn consume_digits(&mut self) {
        while let Some(b'0'..=b'9') = self.peek() {
            self.i += 1;
        }
    }

    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\n' | b'\r' | b'\t')) {
            self.i += 1;
        }
    }

    fn expect(&mut self, byte: u8) -> Result<(), JsonError> {
        match self.next() {
            Some(b) if b == byte => Ok(()),
            _ => Err(JsonError::new("unexpected token")),
        }
    }

    fn expect_bytes(&mut self, needle: &[u8]) -> Result<(), JsonError> {
        if self.consume_bytes(needle) {
            Ok(())
        } else {
            Err(JsonError::new("unexpected token"))
        }
    }

    fn consume_bytes(&mut self, needle: &[u8]) -> bool {
        if self.bytes.get(self.i..self.i + needle.len()) == Some(needle) {
            self.i += needle.len();
            true
        } else {
            false
        }
    }

    fn try_consume(&mut self, byte: u8) -> bool {
        if self.peek() == Some(byte) {
            self.i += 1;
            true
        } else {
            false
        }
    }

    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.i).copied()
    }

    fn next(&mut self) -> Option<u8> {
        let out = self.peek();
        if out.is_some() {
            self.i += 1;
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_object_array_and_string() {
        let value = parse_json(r#"{"a":[1,true,"x"],"b":null}"#).expect("must parse");
        let JsonValue::Object(map) = value else {
            panic!("expected object")
        };
        assert!(matches!(map.get("b"), Some(JsonValue::Null)));
    }

    #[test]
    fn pretty_prints_json() {
        let value = parse_json(r#"{"status":"ok"}"#).expect("must parse");
        let rendered = to_pretty_json(&value);
        assert!(rendered.contains("\"status\""));
    }
}
