use crate::Message;
use cosmic::iced::{
    Subscription,
    futures::{StreamExt, channel::mpsc},
};
use serde_json::Value;
use std::{
    io::{BufRead, BufReader, Write},
    path::Path,
    process::{Child, Command, Stdio},
    sync::{Arc, OnceLock},
    thread,
    time::{Duration, Instant},
};
type Events = Arc<cosmic::iced::futures::lock::Mutex<mpsc::UnboundedReceiver<Message>>>;
static EVENTS: OnceLock<Events> = OnceLock::new();
pub struct Bridge {
    child: Child,
    tx: std::sync::mpsc::Sender<Value>,
}
impl Bridge {
    pub fn start(base: &Path) -> Result<Self, String> {
        let python = std::env::var_os("ELGIN_PYTHON")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| {
                if base.join("python").is_dir() {
                    std::path::PathBuf::from("/usr/bin/python3")
                } else {
                    base.join(".venv/bin/python")
                }
            });
        let mut command = Command::new(python);
        if base.join("python").is_dir() {
            command.env("PYTHONPATH", base.join("python"));
        }
        let mut child = command
            .arg("-u")
            .arg(base.join("bridge/worker.py"))
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|_| {
                "Não foi possível iniciar TinyTuya. Verifique a instalação e o Python 3.12."
                    .to_string()
            })?;
        let input = child.stdin.take().unwrap();
        let output = child.stdout.take().unwrap();
        let (tx, rx) = std::sync::mpsc::channel::<Value>();
        thread::spawn(move || {
            let mut input = input;
            for v in rx {
                if writeln!(input, "{v}").is_err() {
                    break;
                }
            }
        });
        let (etx, erx) = mpsc::unbounded();
        let _ = EVENTS.set(Arc::new(cosmic::iced::futures::lock::Mutex::new(erx)));
        thread::spawn(move || {
            for line in BufReader::new(output).lines() {
                let Ok(line) = line else { break };
                if let Ok(v) = serde_json::from_str(&line)
                    && etx.unbounded_send(Message::Event(v)).is_err()
                {
                    return;
                }
            }
            let _ = etx.unbounded_send(Message::HelperEnded);
        });
        Ok(Self { child, tx })
    }
    pub fn send(&self, v: Value) -> bool {
        self.tx.send(v).is_ok()
    }
}
impl Drop for Bridge {
    fn drop(&mut self) {
        let _ = self.tx.send(serde_json::json!({"op":"quit"}));
        let until = Instant::now() + Duration::from_secs(6);
        loop {
            if matches!(self.child.try_wait(), Ok(Some(_))) {
                return;
            }
            if Instant::now() >= until {
                break;
            }
            thread::sleep(Duration::from_millis(30));
        }
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}
pub fn subscription() -> Subscription<Message> {
    if EVENTS.get().is_none() {
        return Subscription::none();
    }
    Subscription::run(|| {
        cosmic::iced::futures::stream::unfold(EVENTS.get().unwrap().clone(), |rx| async move {
            let next = rx.lock().await.next().await;
            next.map(|message| (message, rx))
        })
        .chain(cosmic::iced::futures::stream::pending())
    })
}
