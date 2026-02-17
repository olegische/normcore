#![no_main]

use libfuzzer_sys::fuzz_target;
use normcore_rs::JsonValue;
use normcore_rs::parse_conversation;
use normcore_rs::parse_json;

fuzz_target!(|data: &[u8]| {
    if let Ok(input) = std::str::from_utf8(data)
        && let Ok(value) = parse_json(input)
        && let JsonValue::Array(messages) = value
    {
        let _ = parse_conversation(&messages);
    }
});
