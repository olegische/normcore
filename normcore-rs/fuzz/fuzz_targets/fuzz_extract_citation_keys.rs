#![no_main]

use libfuzzer_sys::fuzz_target;
use normcore::extract_citation_keys;

fuzz_target!(|data: &[u8]| {
    let input = String::from_utf8_lossy(data);
    let _ = extract_citation_keys(&input);
});
