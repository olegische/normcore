#![no_main]

use libfuzzer_sys::fuzz_target;
use normcore::JsonValue;
use normcore::parse_conversation;
use normcore::parse_json;

fuzz_target!(|data: &[u8]| {
    if let Ok(input) = std::str::from_utf8(data)
        && let Ok(value) = parse_json(input)
        && let JsonValue::Array(messages) = value
    {
        let _ = parse_conversation(&messages);
    }
});
