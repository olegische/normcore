use normcore_rs::EvaluateInput;
use normcore_rs::JsonValue;
use normcore_rs::coerce_grounds_input;
use normcore_rs::evaluate;
use normcore_rs::parse_conversation;
use normcore_rs::parse_json;
use normcore_rs::to_pretty_json;

fn print_help() {
    println!("NormCore CLI.");
    println!("\nUsage:");
    println!(
        "  normcore-rs [--version] [--log-level LEVEL] [-v|-vv] evaluate [--agent-output TEXT] [--conversation JSON] [--grounds JSON]"
    );
}

fn main() {
    std::process::exit(run(std::env::args().collect()));
}

fn run(argv: Vec<String>) -> i32 {
    let args = if argv.is_empty() {
        Vec::new()
    } else {
        argv[1..].to_vec()
    };

    if args.is_empty() {
        print_help();
        return 0;
    }

    if args.iter().any(|a| a == "--version") {
        println!("{}", env!("CARGO_PKG_VERSION"));
        return 0;
    }

    let mut i = 0;
    let mut command = String::new();
    let mut agent_output: Option<String> = None;
    let mut conversation_json: Option<String> = None;
    let mut grounds_json: Option<String> = None;

    while i < args.len() {
        match args[i].as_str() {
            "--log-level" => {
                i += 1;
            }
            "-v" | "-vv" => {}
            "evaluate" => {
                command = "evaluate".to_string();
            }
            "--agent-output" => {
                i += 1;
                if let Some(v) = args.get(i) {
                    agent_output = Some(v.clone());
                } else {
                    eprintln!("error: --agent-output requires value");
                    return 2;
                }
            }
            "--conversation" => {
                i += 1;
                if let Some(v) = args.get(i) {
                    conversation_json = Some(v.clone());
                } else {
                    eprintln!("error: --conversation requires value");
                    return 2;
                }
            }
            "--grounds" => {
                i += 1;
                if let Some(v) = args.get(i) {
                    grounds_json = Some(v.clone());
                } else {
                    eprintln!("error: --grounds requires value");
                    return 2;
                }
            }
            _ => {}
        }
        i += 1;
    }

    if command != "evaluate" {
        print_help();
        return 0;
    }

    let conversation = match conversation_json {
        Some(raw) => match parse_json(&raw) {
            Ok(JsonValue::Array(arr)) => match parse_conversation(&arr) {
                Ok(v) => Some(v),
                Err(err) => {
                    eprintln!("error: invalid --conversation: {err:?}");
                    return 2;
                }
            },
            Ok(_) => {
                eprintln!("error: --conversation must be JSON array");
                return 2;
            }
            Err(err) => {
                eprintln!(
                    "error: Failed to parse --conversation JSON: {}",
                    err.message
                );
                return 2;
            }
        },
        None => None,
    };

    let grounds = match grounds_json {
        Some(raw) => match parse_json(&raw) {
            Ok(JsonValue::Array(arr)) => Some(coerce_grounds_input(Some(&arr), None, None)),
            Ok(_) => {
                eprintln!("error: --grounds must be JSON array");
                return 2;
            }
            Err(err) => {
                eprintln!("error: Failed to parse --grounds JSON: {}", err.message);
                return 2;
            }
        },
        None => None,
    };

    match evaluate(EvaluateInput {
        agent_output,
        conversation,
        grounds,
    }) {
        Ok(judgment) => {
            println!("{}", to_pretty_json(&judgment.to_json_value()));
            0
        }
        Err(err) => {
            eprintln!("error: {err:?}");
            2
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn help_runs() {
        assert_eq!(run(vec!["normcore-rs".to_string()]), 0);
    }

    #[test]
    fn version_runs() {
        assert_eq!(
            run(vec!["normcore-rs".to_string(), "--version".to_string()]),
            0
        );
    }

    #[test]
    fn evaluate_runs() {
        assert_eq!(
            run(vec![
                "normcore-rs".to_string(),
                "evaluate".to_string(),
                "--agent-output".to_string(),
                "The deployment is blocked.".to_string(),
            ]),
            0
        );
    }
}
